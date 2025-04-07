""" TypeScript/JavaScript specific extractors for CodeHem. """

# Import existing and new extractors to ensure they are discovered by the registry
from . import typescript_class_extractor
from . import typescript_function_extractor
from . import typescript_import_extractor
from . import typescript_interface_extractor
from . import typescript_method_extractor # Handles methods, getters, setters
from . import typescript_property_extractor
from . import typescript_static_property_extractor
from . import typescript_decorator_extractor
from . import typescript_enum_extractor
from . import typescript_namespace_extractor
from . import typescript_type_alias_extractor

__all__ = [
    'typescript_class_extractor',
    'typescript_function_extractor',
    'typescript_import_extractor',
    'typescript_interface_extractor',
    'typescript_method_extractor',
    'typescript_property_extractor',
    'typescript_static_property_extractor',
    'typescript_decorator_extractor',
    'typescript_enum_extractor',
    'typescript_namespace_extractor',
    'typescript_type_alias_extractor',
]