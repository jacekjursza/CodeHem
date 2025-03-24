"""
Central registration system for CodeHem components.
Uses decorator-based self-registration for automatic component discovery.
"""
import importlib
import logging
import os
from typing import Any, List, Optional, Type

import rich

logger = logging.getLogger(__name__)

class Registry:
    """
    Central registry for all CodeHem components.
    Components register themselves using decorators.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Registry, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize empty registries for different component types."""
        self.language_detectors = {}
        self.language_services = {}
        self.extractors = {}
        self.handlers = {}
        self.discovered_modules = set()
        self._initialized = False

    def register_language_detector(self, cls):
        """Register a language detector class."""
        instance = cls()
        language_code = instance.language_code.lower()
        self.language_detectors[language_code] = instance
        rich.print(f"Registered language detector: {cls.__name__} for {language_code}")
        return cls

    def register_language_service(self, cls):
        """Register a language service class."""
        instance = cls()
        language_code = instance.language_code.lower()
        self.language_services[language_code] = instance
        rich.print(f"Registered language service: {cls.__name__} for {language_code}")
        return cls

    def register_extractor(self, cls):
        """Register an extractor class."""
        instance = cls()
        element_type = instance.element_type.value.lower()
        self.extractors[element_type] = cls
        rich.print(f"Registered extractor: {cls.__name__} for {element_type}")
        return cls

    def register_handler(self, cls):
        """Register a language-specific handler."""
        instance = cls()
        language_code = instance.language_code.lower()
        element_type = instance.element_type.value.lower()
        
        if language_code not in self.handlers:
            self.handlers[language_code] = {}
        
        self.handlers[language_code][element_type] = instance
        rich.print(f"Registered handler: {cls.__name__} for {language_code}/{element_type}")
        return cls

    def get_language_detector(self, language_code: str) -> Optional[Any]:
        """Get a language detector by code."""
        return self.language_detectors.get(language_code.lower())

    def get_language_service(self, language_code: str) -> Optional[Any]:
        """Get a language service by code."""
        return self.language_services.get(language_code.lower())

    def get_extractor(self, element_type: str) -> Optional[Type]:
        """Get an extractor class by element type."""
        if hasattr(element_type, 'value'):
            element_type = element_type.value
        return self.extractors.get(element_type.lower())

    def get_handler(self, language_code: str, element_type: str) -> Optional[Any]:
        """Get a handler for a specific language and element type."""
        language_code = language_code.lower()
        element_type = element_type.lower()
        return self.handlers.get(language_code, {}).get(element_type)

    def get_handlers(self, language_code: str) -> List[Any]:
        """Get all handlers for a specific language."""
        language_code = language_code.lower()
        return list(self.handlers.get(language_code, {}).values())

    def get_supported_languages(self) -> List[str]:
        """Get a list of all supported language codes."""
        return list(self.language_services.keys())

    def discover_modules(self, package_name="codehem", recursive=True):
        """
        Discover and import all modules in a package to trigger registrations.
        """
        rich.print(f"Discovering modules in package: {package_name}")
        
        try:
            package = importlib.import_module(package_name)
            package_dir = os.path.dirname(package.__file__)
            
            for item in os.listdir(package_dir):
                # Skip __pycache__ and hidden directories
                if item.startswith('__') or item.startswith('.'):
                    continue
                
                # Full path to the item
                full_path = os.path.join(package_dir, item)
                
                # If it's a Python file, import it
                if item.endswith('.py'):
                    module_name = f"{package_name}.{item[:-3]}"
                    if module_name not in self.discovered_modules:
                        try:
                            importlib.import_module(module_name)
                            self.discovered_modules.add(module_name)
                            rich.print(f"Imported module: {module_name}")
                        except Exception as e:
                            logger.warning(f"Error importing module {module_name}: {e}")
                
                # If it's a directory and recursive is True, process it as a subpackage
                elif os.path.isdir(full_path) and recursive:
                    subpackage = f"{package_name}.{item}"
                    # Check if it's a Python package (has __init__.py)
                    if os.path.exists(os.path.join(full_path, "__init__.py")):
                        self.discover_modules(subpackage, recursive)
        
        except Exception as e:
            logger.error(f"Error discovering modules in {package_name}: {e}")
    
    def initialize_components(self):
        """
        Discover and initialize all components.
        This should be called once at application startup.
        """
        if self._initialized:
            return

        # Discover and import all modules to trigger registrations
        self.discover_modules()
        
        # Create instances of any registered classes if needed
        # Currently, the registration decorators already create instances
        
        self._initialized = True

        rich.print(f"Components initialized: "
                   f"{len(self.language_detectors)} detectors, "
                   f"{len(self.language_services)} services, "
                   f"{len(self.extractors)} extractors, "
                   f"{len(self.handlers)} languages with handlers")


# Create a singleton registry instance
registry = Registry()

# Decorator functions for self-registration
def language_detector(cls):
    """Decorator to register a language detector."""
    return registry.register_language_detector(cls)

def language_service(cls):
    """Decorator to register a language service."""
    return registry.register_language_service(cls)

def extractor(cls):
    """Decorator to register an extractor."""
    return registry.register_extractor(cls)

def handler(cls):
    """Decorator to register a language handler."""
    return registry.register_handler(cls)