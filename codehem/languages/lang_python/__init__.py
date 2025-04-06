# MODIFIED FILE: Import new extractor modules
""" Python language module for CodeHem. """
# Import service, components etc.
from . import service # Registers PythonLanguageService
from . import config # Registers LANGUAGE_CONFIG
from . import detector # Registers PythonLanguageDetector
from . import formatting # Imports PythonFormatter (used by service/config)
# Import manipulator modules to register them
from .manipulator import base
from .manipulator import class_handler
from .manipulator import function_handler
from .manipulator import import_handler
from .manipulator import method_handler
from .manipulator import property_handler
# Import type descriptor modules to register them
from . import type_class
from . import type_decorator # Needed if we have decorator extractor/manipulator
from . import type_function
from . import type_import
from . import type_method
from . import type_property_getter
from . import type_property_setter
from . import type_static_property
# Import existing extractor modules (if any were already in lang_python)
# Example: from .extractors import python_property_extractor # If kept

# *** CHANGE START: Import new extractor modules ***
# Ensure the extractors package is recognized
from . import extractors
# The line above might be sufficient if __init__.py inside extractors imports the specific files.
# Alternatively, be more explicit (safer if __init__.py is simple):
# from .extractors import python_decorator_extractor
# from .extractors import python_property_getter_extractor
# from .extractors import python_property_setter_extractor
# *** CHANGE END ***