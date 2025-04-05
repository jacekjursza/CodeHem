import importlib
import logging
import os
import traceback
from typing import Any, List, Optional, Type
import rich
from codehem.core.language_service import LanguageService
from codehem.core.extractors.base import BaseExtractor

logger = logging.getLogger(__name__)

class Registry:
    """Central registry for CodeHem components."""
    _instance = None

    def __init__(self):
        self._initialized = False
        self._initialize()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
        return cls._instance

    def _initialize(self):
        """Initializes empty registries."""
        if hasattr(self, '_initialized') and self._initialized:
            return
        self.language_detectors = {}
        self.language_services = {}
        self.all_descriptors = {}
        self.all_extractors = {}
        self.all_manipulators = {}
        self.discovered_modules = set()
        self.language_service_instances = {}
        self._initialized = False
        logger.debug('Registry _initialize completed.')

    def register_language_detector(self, cls):
        """Registers a language detector class."""
        try:
            instance = cls()
            language_code = instance.language_code.lower()
            if language_code in self.language_detectors:
                logger.warning(f"Language detector for '{language_code}' is already registered ({self.language_detectors[language_code].__class__.__name__}). Overwriting with {cls.__name__}.")
            self.language_detectors[language_code] = instance
            rich.print(f'Registered language detector: {cls.__name__} for {language_code}')
        except Exception as e:
            logger.error(f'Error during registration of language detector {cls.__name__}: {e}', exc_info=True)
        return cls

    def register_language_service(self, cls: Type[LanguageService]):
        """Registers a language service class."""
        try:
            language_code = cls.LANGUAGE_CODE.lower()
            if language_code in self.language_services:
                logger.warning(f"Language service for '{language_code}' is already registered ({self.language_services[language_code].__name__}). Overwriting with {cls.__name__}.")
            self.language_services[language_code] = cls
            rich.print(f'Registered language service: {cls.__name__} for {language_code}')
        except Exception as e:
            logger.error(f'Error during registration of language service {cls.__name__}: {e}', exc_info=True)
        return cls

    def register_extractor(self, cls: Type[BaseExtractor]):
        """Registers an extractor class."""
        try:
            language_code = cls.LANGUAGE_CODE.lower()
            element_type = cls.ELEMENT_TYPE.value.lower()
            extractor_key = f'{language_code}/{element_type}'
            if extractor_key in self.all_extractors:
                logger.warning(f"Extractor for '{extractor_key}' is already registered ({self.all_extractors[extractor_key].__name__}). Overwriting with {cls.__name__}.")
            self.all_extractors[extractor_key] = cls
            rich.print(f'Registered extractor: {cls.__name__} for {extractor_key}')
        except Exception as e:
            logger.error(f'Error during registration of extractor {cls.__name__}: {e}', exc_info=True)
        return cls

    def register_manipulator(self, cls):
        """Registers a manipulator class."""
        try:
            language_code = cls.LANGUAGE_CODE.lower()
            element_type = cls.ELEMENT_TYPE.value.lower()
            key = f'{language_code}_{element_type}'
            if key in self.all_manipulators:
                logger.warning(f"Manipulator for '{key}' is already registered ({self.all_manipulators[key].__name__}). Overwriting with {cls.__name__}.")
            self.all_manipulators[key] = cls
            rich.print(f'Registered manipulator: {cls.__name__} for {language_code}/{element_type}')
        except Exception as e:
            logger.error(f'Error during registration of manipulator {cls.__name__}: {e}', exc_info=True)
        return cls

    def register_element_type_descriptor(self, cls):
        """Registers an element type descriptor class."""
        try:
            instance = cls()
            language_code = instance.language_code.lower()
            element_type = instance.element_type.value.lower()
            if language_code not in self.all_descriptors:
                self.all_descriptors[language_code] = {}
            if element_type in self.all_descriptors[language_code]:
                logger.warning(f"Descriptor for '{language_code}/{element_type}' is already registered ({self.all_descriptors[language_code][element_type].__class__.__name__}). Overwriting with {cls.__name__}.")
            self.all_descriptors[language_code][element_type] = instance
            rich.print(f'Registered descriptor: {cls.__name__} for {language_code}/{element_type}')
        except Exception as e:
            logger.error(f'Error during registration of descriptor {cls.__name__}: {e}', exc_info=True)
        return cls

    def get_language_detector(self, language_code: str) -> Optional[Any]:
        """Gets a language detector instance."""
        return self.language_detectors.get(language_code.lower())

    def get_language_service(self, language_code: str) -> Optional[LanguageService]:
        """Gets or creates a language service instance (singleton per language)."""
        if not isinstance(language_code, str):
            logger.error(f'Invalid language_code type: {type(language_code)}')
            return None
        lang_code_lower = language_code.lower()
        if lang_code_lower in self.language_service_instances:
            logger.debug(f"Returning existing LanguageService instance for '{lang_code_lower}'.")
            return self.language_service_instances[lang_code_lower]

        language_service_cls = self.language_services.get(lang_code_lower)
        if not language_service_cls:
            logger.error(f"No registered LanguageService class found for '{lang_code_lower}'.")
            return None

        logger.debug(f"Creating new LanguageService instance for '{lang_code_lower}'.")
        try:
            # Dynamically get formatter class based on language code (example for Python)
            formatter_class = None
            if lang_code_lower == 'python':
                from codehem.languages.lang_python.formatting.python_formatter import PythonFormatter
                formatter_class = PythonFormatter
            # Add similar logic here for other languages if they have specific formatters

            instance = language_service_cls(
                extractors=self.all_extractors,
                manipulators=self.all_manipulators,
                element_type_descriptors=self.all_descriptors,
                formatter_class=formatter_class
            )
            self.language_service_instances[lang_code_lower] = instance
            logger.debug(f"Created and cached LanguageService instance for '{lang_code_lower}'.")
            return instance
        except Exception as e:
            logger.exception(f"Critical error during LanguageService initialization for '{lang_code_lower}': {e}")
            return None

    def get_supported_languages(self) -> List[str]:
        """Returns a list of supported language codes."""
        return list(self.language_services.keys())

    def discover_modules(self, package_name='codehem', recursive=True):
        """Discovers and imports modules in the package to trigger registration."""
        rich.print(f'Discovering modules in package: {package_name}')
        try:
            package = importlib.import_module(package_name)
            package_dir = os.path.dirname(package.__file__)

            for item in os.listdir(package_dir):
                full_path = os.path.join(package_dir, item)
                if item.startswith('_') or item.startswith('.'):
                    continue

                if item.endswith('.py'):
                    module_name = f'{package_name}.{item[:-3]}'
                    if module_name not in self.discovered_modules:
                        try:
                            importlib.import_module(module_name)
                            self.discovered_modules.add(module_name)
                        except ModuleNotFoundError:
                             logger.warning(f'Cannot import module {module_name} (not found).')
                        except Exception as e:
                            # Log only a summary to avoid cluttering logs during discovery
                            logger.warning(f'Error importing module {module_name}: {e}\n{traceback.format_exc(limit=1)}')
                elif os.path.isdir(full_path) and recursive:
                    # Check if it's a package (contains __init__.py)
                    if os.path.exists(os.path.join(full_path, '__init__.py')):
                        subpackage_name = f'{package_name}.{item}'
                        self.discover_modules(subpackage_name, recursive=recursive)

        except ModuleNotFoundError:
            logger.error(f'Cannot find starting package: {package_name}')
        except Exception as e:
            logger.error(f'Error discovering modules in {package_name}: {e}', exc_info=True)

    def initialize_components(self):
        """Discovers and initializes all components. Called once."""
        if self._initialized:
            logger.debug('Components already initialized.')
            return

        logger.info('Starting CodeHem component initialization...')
        self.discover_modules() # Discover components in the main package and subpackages
        self._initialized = True
        rich.print(f'Components initialized: {len(self.language_detectors)} detectors, {len(self.language_services)} services, {len(self.all_extractors)} extractors, {len(self.all_manipulators)} manipulators registered.')
        logger.info('Component initialization finished.')

# Global registry instance
registry = Registry()

# Decorators for registration
def language_detector(cls):
    """Decorator for registering a language detector."""
    return registry.register_language_detector(cls)

def language_service(cls):
    """Decorator for registering a language service."""
    return registry.register_language_service(cls)

def extractor(cls):
    """Decorator for registering an extractor."""
    return registry.register_extractor(cls)

def manipulator(cls):
    """Decorator for registering a manipulator."""
    return registry.register_manipulator(cls)

def element_type_descriptor(cls):
    """Decorator for registering an element type descriptor."""
    return registry.register_element_type_descriptor(cls)