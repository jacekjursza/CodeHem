# MODIFIED FILE: Changed LanguageService import to string literal to fix circular import
import importlib
import importlib.metadata as importlib_metadata
import logging
import os
import sys # Added sys import for checking module existence
import traceback
from typing import Any, List, Optional, Type, Dict, TYPE_CHECKING # Added Dict, TYPE_CHECKING

import rich
# *** CHANGE START ***
# Use TYPE_CHECKING block for LanguageService import or string literals
# from codehem.core.language_service import LanguageService # Removed direct import
if TYPE_CHECKING:
    from codehem.core.language_service import LanguageService # Keep for type checkers
# *** CHANGE END ***
from codehem.core.extractors.base import BaseExtractor
from codehem.core.manipulators.manipulator_base import ManipulatorBase
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor

logger = logging.getLogger(__name__)

class Registry:
    """Central registry for CodeHem components."""
    _instance = None

    def __init__(self):
        # Prevent re-initialization
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = False
        self._initialize()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
        return cls._instance

    def _initialize(self):
        """Initializes empty registries. Only runs once."""
        logger.debug('Registry initializing...')
        self.language_detectors: Dict[str, Any] = {} # Type hint added
        self.language_services: Dict[str, Type['LanguageService']] = {} # Type hint added, uses string literal
        self.all_descriptors: Dict[str, Dict[str, ElementTypeLanguageDescriptor]] = {} # Type hint added
        self.all_extractors: Dict[str, Type[BaseExtractor]] = {} # Type hint added
        self.all_manipulators: Dict[str, Type[ManipulatorBase]] = {} # Type hint added
        self.language_configs: Dict[str, Dict] = {}
        self.discovered_modules: set[str] = set() # Type hint added
        # Cache for LanguageService instances
        self.language_service_instances: Dict[str, 'LanguageService'] = {} # Type hint added, uses string literal
        logger.debug('Registry _initialize completed.')

    def register_language_detector(self, cls):
        """Registers a language detector class."""
        try:
            instance = cls()
            # Add check for necessary attribute
            if not hasattr(instance, 'language_code'):
                 raise AttributeError(f"Detector class {cls.__name__} needs a 'language_code' attribute.")
            language_code = instance.language_code.lower()
            if language_code in self.language_detectors:
                logger.warning(f"Language detector for '{language_code}' is already registered ({self.language_detectors[language_code].__class__.__name__}). Overwriting with {cls.__name__}.")
            self.language_detectors[language_code] = instance
            rich.print(f'Registered language detector: {cls.__name__} for {language_code}')
        except Exception as e:
             logger.error(f"Failed to register language detector {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_language_service(self, cls: Type['LanguageService']): # Type hint uses string literal
        """Registers a language service class."""
        try:
            if not hasattr(cls, 'LANGUAGE_CODE') or not cls.LANGUAGE_CODE:
                 raise ValueError(f"LanguageService class {cls.__name__} must define LANGUAGE_CODE.")
            language_code = cls.LANGUAGE_CODE.lower()
            if language_code in self.language_services:
                logger.warning(f"Language service for '{language_code}' is already registered ({self.language_services[language_code].__name__}). Overwriting with {cls.__name__}.")
            self.language_services[language_code] = cls
            rich.print(f'Registered language service: {cls.__name__} for {language_code}')
        except Exception as e:
            logger.error(f"Failed to register language service {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_extractor(self, cls: Type[BaseExtractor]):
        """Registers an extractor class."""
        try:
            if not hasattr(cls, 'LANGUAGE_CODE') or not hasattr(cls, 'ELEMENT_TYPE'):
                 raise ValueError(f"Extractor class {cls.__name__} must define LANGUAGE_CODE and ELEMENT_TYPE.")
            language_code = cls.LANGUAGE_CODE.lower()
            element_type = cls.ELEMENT_TYPE.value.lower()
            extractor_key = f'{language_code}/{element_type}'
            if extractor_key in self.all_extractors:
                logger.warning(f"Extractor for '{extractor_key}' is already registered ({self.all_extractors[extractor_key].__name__}). Overwriting with {cls.__name__}.")
            self.all_extractors[extractor_key] = cls
            rich.print(f'Registered extractor: {cls.__name__} for {extractor_key}')
        except Exception as e:
            logger.error(f"Failed to register extractor {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_manipulator(self, cls: Type[ManipulatorBase]):
        """Registers a manipulator class."""
        try:
            if not hasattr(cls, 'LANGUAGE_CODE') or not hasattr(cls, 'ELEMENT_TYPE'):
                 raise ValueError(f"Manipulator class {cls.__name__} must define LANGUAGE_CODE and ELEMENT_TYPE.")
            language_code = cls.LANGUAGE_CODE.lower()
            element_type = cls.ELEMENT_TYPE.value.lower()
            key = f'{language_code}_{element_type}'
            if key in self.all_manipulators:
                logger.warning(f"Manipulator for '{key}' is already registered ({self.all_manipulators[key].__name__}). Overwriting with {cls.__name__}.")
            self.all_manipulators[key] = cls
            rich.print(f'Registered manipulator: {cls.__name__} for {language_code}/{element_type}')
        except Exception as e:
             logger.error(f"Failed to register manipulator {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_element_type_descriptor(self, cls: Type[ElementTypeLanguageDescriptor]):
        """Registers an element type descriptor class instance."""
        try:
            instance = cls()
            if not hasattr(instance, 'language_code') or not hasattr(instance, 'element_type'):
                 raise ValueError(f"ElementTypeLanguageDescriptor class {cls.__name__} instance must have language_code and element_type.")
            language_code = instance.language_code.lower()
            element_type = instance.element_type.value.lower()

            if language_code not in self.all_descriptors:
                self.all_descriptors[language_code] = {}
            if element_type in self.all_descriptors[language_code]:
                logger.warning(f"Descriptor for '{language_code}/{element_type}' is already registered ({self.all_descriptors[language_code][element_type].__class__.__name__}). Overwriting with {cls.__name__}.")
            self.all_descriptors[language_code][element_type] = instance
            rich.print(f'Registered descriptor: {cls.__name__} for {language_code}/{element_type}')
        except Exception as e:
            logger.error(f"Failed to register element type descriptor {cls.__name__}: {e}", exc_info=True)
        return cls

    def register_language_config(self, language_code: str, config: Dict):
        """Stores the configuration dictionary for a language."""
        lang_code_lower = language_code.lower()
        if lang_code_lower in self.language_configs:
            logger.warning(f"Language config for '{lang_code_lower}' is already registered. Overwriting.")
        self.language_configs[lang_code_lower] = config
        logger.debug(f"Registered language config for '{lang_code_lower}'. Keys: {list(config.keys())}")

    def get_language_config(self, language_code: str) -> Optional[Dict]:
        """Retrieves the stored configuration dictionary for a language."""
        return self.language_configs.get(language_code.lower())

    def get_language_detector(self, language_code: str) -> Optional[Any]:
        """Gets a language detector instance."""
        return self.language_detectors.get(language_code.lower())

    # *** CHANGE START ***
    # Updated return type hint to use string literal
    def get_language_service(self, language_code: str) -> Optional['LanguageService']:
    # *** CHANGE END ***
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

        logger.debug(f"Attempting to create new LanguageService instance for '{lang_code_lower}'.")

        lang_config = self.get_language_config(lang_code_lower)
        formatter_class = None
        if lang_config:
             # Attempt to get formatter_class from the loaded config
             formatter_class = lang_config.get('formatter_class')
             if formatter_class:
                  logger.debug(f"Using formatter {formatter_class.__name__} from config for {lang_code_lower}")
        else:
            logger.warning(f"No language config found for '{lang_code_lower}' when creating service.")

        try:
            # Instantiate the service, passing only the formatter class found (if any)
            # The service __init__ will handle initializing its components
            instance = language_service_cls(
                formatter_class=formatter_class
                # Pass language_code explicitly if needed by __init__ and not set via class attr
                # language_code=lang_code_lower
            )
            self.language_service_instances[lang_code_lower] = instance
            logger.debug(f"Created and cached LanguageService instance for '{lang_code_lower}'.")
            return instance
        except Exception as e:
             logger.error(f"Failed to instantiate LanguageService {language_service_cls.__name__} for {lang_code_lower}: {e}", exc_info=True)
             return None

    def get_supported_languages(self) -> List[str]:
        """Returns a list of supported language codes based on registered services."""
        return list(self.language_services.keys())

    def discover_modules(self, package_name='codehem', recursive=True):
        """Discovers and imports modules in the package to trigger registration."""
        # Avoid printing during discovery unless debugging
        # rich.print(f'Discovering modules in package: {package_name}')
        logger.debug(f"Discovering modules in package: {package_name}")
        try:
            package = importlib.import_module(package_name)
        except ModuleNotFoundError:
             logger.error(f'Cannot find starting package for discovery: {package_name}')
             return

        # Handle packages with or without __file__ (like namespace packages)
        try:
             # Prefer __path__ for directories
             package_dirs = getattr(package, '__path__', [os.path.dirname(package.__file__)])
        except AttributeError:
             logger.warning(f"Package {package_name} seems to lack both __path__ and __file__. Cannot discover.")
             return

        for package_dir in package_dirs:
             if not os.path.isdir(package_dir): # Skip if path isn't a directory
                  continue
             logger.debug(f"Scanning directory: {package_dir}")
             try:
                  items = os.listdir(package_dir)
             except FileNotFoundError:
                  logger.warning(f"Directory not found during discovery: {package_dir}")
                  continue # Skip this directory if it doesn't exist

             for item in items:
                 full_path = os.path.join(package_dir, item)
                 if item.startswith('_') or item.startswith('.'):
                     continue

                 if item.endswith('.py'):
                     module_name = f'{package_name}.{item[:-3]}'
                     if module_name not in self.discovered_modules:
                         try:
                             logger.debug(f"Attempting to import module: {module_name}")
                             imported_module = importlib.import_module(module_name)
                             self.discovered_modules.add(module_name)
                             logger.debug(f"Successfully imported: {module_name}")

                             # Check for LANGUAGE_CONFIG and register it
                             if hasattr(imported_module, 'LANGUAGE_CONFIG') and isinstance(imported_module.LANGUAGE_CONFIG, dict):
                                 config = imported_module.LANGUAGE_CONFIG
                                 if 'language_code' in config:
                                     self.register_language_config(config['language_code'], config)
                                 else:
                                     logger.warning(f"Found LANGUAGE_CONFIG in {module_name} but it lacks 'language_code' key.")

                         except ModuleNotFoundError as mnfe:
                              logger.warning(f'Cannot import module {module_name}. Reason: {mnfe}. Check dependencies or structure.')
                         except Exception as e:
                              logger.error(f"Error importing module {module_name}: {e}\n{traceback.format_exc(limit=1)}") # Limit traceback length

                 elif os.path.isdir(full_path) and recursive:
                     # Check if it's a package (contains __init__.py) before recursing
                    if os.path.exists(os.path.join(full_path, '__init__.py')):
                        subpackage_name = f'{package_name}.{item}'
                        self.discover_modules(subpackage_name, recursive=recursive)

    def _load_entry_point_plugins(self, group: str = 'codehem.languages') -> None:
        """Load language modules declared as entry points."""
        try:
            eps = importlib_metadata.entry_points(group=group)
        except Exception as exc:
            logger.error("Failed to read entry points: %s", exc)
            return

        for ep in eps:
            module_name = ep.value.split(':')[0]
            if module_name in self.discovered_modules:
                continue
            try:
                logger.debug("Loading plugin module '%s' from entry point '%s'", module_name, ep.name)
                importlib.import_module(module_name)
                self.discovered_modules.add(module_name)
                # Discover submodules in the plugin package
                self.discover_modules(module_name)
            except Exception as exc:
                logger.error("Failed to load plugin module %s: %s", module_name, exc)

    def initialize_components(self):
        """Discovers and initializes all components. Called once."""
        if self._initialized:
            logger.debug('Components already initialized.')
            return
        logger.info('Starting CodeHem component initialization...')
        self.discover_modules()  # Discover built-in modules
        self._load_entry_point_plugins()  # Load plugin packages via entry points
        self._initialized = True
        # Log summary after initialization
        logger.info('--- Registry Content After Discovery ---')
        logger.info('Language Detectors: %s', list(self.language_detectors.keys()))
        logger.info('Language Services: %s', list(self.language_services.keys()))
        logger.info('Language Configs: %s', list(self.language_configs.keys()))
        # Limit descriptor output for brevity
        descriptor_summary = {
            lang: f"{len(descs)} descriptors" for lang, descs in self.all_descriptors.items()
        }
        logger.info('All Descriptors: %s', descriptor_summary)
        logger.info('All Extractors: %d registered classes', len(self.all_extractors))
        logger.info('All Manipulators: %d registered classes', len(self.all_manipulators))
        logger.info('--- End Registry Content ---')
        # Use rich.print for the final summary line if preferred
        rich.print(f'Components initialized: {len(self.language_detectors)} detectors, {len(self.language_services)} services, {len(self.language_configs)} configs, {len(self.all_extractors)} extractors, {len(self.all_manipulators)} manipulators registered.')
        logger.info('Component initialization finished.')

# Singleton instance
registry = Registry()

# Add a component registration method for the new architecture
def register_component(self, language_code: str, component_type: str, component_class: Any) -> None:
    """
    Registers a component class for the new component-based architecture.
    This is a temporary bridge method to handle component registration.
    
    Args:
        language_code: The language code the component is for
        component_type: The type of component (e.g., 'code_parser', 'syntax_tree_navigator')
        component_class: The component class to register
    """
    logger.debug(f"Registering component: {component_class.__name__} as {component_type} for {language_code}")
    # In the future, this would store components in a structured way
    # For now, we'll just log it and not block initialization
    print(f"Registered component: {component_class.__name__} as {component_type} for {language_code}")

# Decorators remain the same
def language_detector(cls):
    return registry.register_language_detector(cls)

def language_service(cls):
    return registry.register_language_service(cls)

def extractor(cls):
    return registry.register_extractor(cls)

def manipulator(cls):
    return registry.register_manipulator(cls)

def element_type_descriptor(cls):
    return registry.register_element_type_descriptor(cls)