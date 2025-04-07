"""
TypeScript/JavaScript language module for CodeHem.
Leverages the tree-sitter-typescript grammar.
This __init__ intentionally only imports core components needed early
to avoid circular dependencies during registry discovery.
Other components like type descriptors, extractors, and manipulators should be imported
directly by the modules that use them or discovered dynamically by the registry
and language service.
"""
from . import config
from . import detector
from . import service
from . import typescript_post_processor
from .formatting import typescript_formatter

# Import newly added type descriptors to ensure registration
from . import type_class
from . import type_function
from . import type_import
from . import type_interface
from . import type_method
from . import type_property
from . import type_static_property
from . import type_decorator
from . import type_alias
from . import type_enum
from . import type_namespace
from . import type_property_getter
from . import type_property_setter