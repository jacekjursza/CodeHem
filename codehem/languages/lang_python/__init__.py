"""Python language module for CodeHem."""
# Import service, components and other modules
from .service import PythonLanguageService
from .config import LANGUAGE_CONFIG
from .detector import PythonLanguageDetector
from .formatting.python_formatter import PythonFormatter

# Import components for registration and access
from .components import (
    PythonCodeParser,
    PythonSyntaxTreeNavigator,
    PythonElementExtractor,
    PythonExtractionOrchestrator,
    PythonPostProcessor
)

# Import manipulator modules to register them
from .manipulator import base
from .manipulator import class_handler
from .manipulator import function_handler
from .manipulator import import_handler
from .manipulator import method_handler
from .manipulator import property_handler

# Import type descriptor modules to register them
from . import type_class
from . import type_decorator
from . import type_function
from . import type_import
from . import type_method
from . import type_property_getter
from . import type_property_setter
from . import type_static_property

# Import extractors for registration
from .extractors import python_decorator_extractor
from .extractors import python_property_extractor
from .extractors import python_property_getter_extractor
from .extractors import python_property_setter_extractor
