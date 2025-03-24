import logging
from typing import Dict, Any, Optional, List, Type

logger = logging.getLogger(__name__)

class ManipulatorRegistry:
    """Registry for manipulator components."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ManipulatorRegistry, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize empty registries."""
        self.manipulators = {}  # element_type -> manipulator class
        self.handlers = {}      # language_code -> {element_type -> handler instance}
        self._initialized = False

    def register_manipulator(self, cls):
        """Register a manipulator class."""
        instance = cls()
        element_type = instance.element_type.value.lower()
        self.manipulators[element_type] = cls
        logger.debug(f'Registered manipulator: {cls.__name__} for {element_type}')
        return cls

    def register_handler(self, cls):
        """Register a language-specific handler."""
        instance = cls()
        language_code = instance.language_code.lower()
        element_type = instance.element_type.value.lower()
        if language_code not in self.handlers:
            self.handlers[language_code] = {}
        self.handlers[language_code][element_type] = instance
        logger.debug(f'Registered handler: {cls.__name__} for {language_code}/{element_type}')
        return cls

    def get_manipulator(self, element_type: str) -> Optional[Type]:
        """Get a manipulator by element type."""
        if hasattr(element_type, 'value'):
            element_type = element_type.value
        return self.manipulators.get(element_type.lower())

    def get_handler(self, language_code: str, element_type: str) -> Optional[Any]:
        """Get a handler for a specific language and element type."""
        language_code = language_code.lower()
        element_type = element_type.lower()
        return self.handlers.get(language_code, {}).get(element_type)

    def get_supported_languages(self) -> List[str]:
        """Get a list of all supported language codes."""
        return list(self.handlers.keys())

    def initialize_components(self):
        """Discover and initialize all components."""
        if self._initialized:
            return
        # We could add discovery logic here similar to the extractor system
        self._initialized = True
        logger.debug(f'Manipulator components initialized: {len(self.manipulators)} manipulators, {len(self.handlers)} handlers')

registry = ManipulatorRegistry()

def manipulator(cls):
    """Decorator to register a manipulator."""
    return registry.register_manipulator(cls)

def handler(cls):
    """Decorator to register a language handler."""
    return registry.register_handler(cls)