"""
TypeScript/JavaScript language module for CodeHem.
Leverages the tree-sitter-typescript grammar.
This __init__ intentionally only imports core components needed early
to avoid circular dependencies during registry discovery.
Other components like type descriptors, extractors, and manipulators should be imported
directly by the modules that use them or discovered dynamically by the registry
and language service.
"""

from . import config  # noqa: F401
from . import detector  # noqa: F401
from . import service  # noqa: F401
from . import components  # noqa: F401 - Register components
from .formatting import typescript_formatter  # noqa: F401

# Import newly added type descriptors to ensure registration
from . import type_class  # noqa: F401
from . import type_function  # noqa: F401
from . import type_import  # noqa: F401
from . import type_interface  # noqa: F401
from . import type_method  # noqa: F401
from . import type_property  # noqa: F401
from . import type_static_property  # noqa: F401
from . import type_decorator  # noqa: F401
from . import type_alias  # noqa: F401
from . import type_enum  # noqa: F401
from . import type_namespace  # noqa: F401
from . import type_property_getter  # noqa: F401
from . import type_property_setter  # noqa: F401

# Register manipulators
from .manipulator import base  # noqa: F401

# Register post-processor with factory
from codehem.core.post_processors.factory import PostProcessorFactory
PostProcessorFactory.register('typescript', 'codehem.languages.lang_typescript.typescript_post_processor.TypeScriptExtractionPostProcessor')
