# NEW FILE: Initializes the Python extractors package
""" Python-specific extractors for CodeHem. """
from . import python_decorator_extractor
from . import python_property_getter_extractor
from . import python_property_setter_extractor

# Optional: Define __all__ if needed for explicit exports
__all__ = [
    'python_decorator_extractor',
    'python_property_getter_extractor',
    'python_property_setter_extractor'
]