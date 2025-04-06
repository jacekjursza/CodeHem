"""
TypeScript/JavaScript language module for CodeHem.
Leverages the tree-sitter-typescript grammar.

This __init__ intentionally only imports core components needed early
to avoid circular dependencies during registry discovery. Other components
like type descriptors, extractors, and manipulators should be imported
directly by the modules that use them or discovered dynamically by the registry
and language service.
"""
# Import main components needed for service instantiation and basic registration
from . import config
from . import detector
from . import service
from . import typescript_post_processor
from .formatting import typescript_formatter

# DO NOT import type_*, extractors.*, manipulator.* here directly
# They will be discovered by the registry scanning mechanism or loaded by the service.