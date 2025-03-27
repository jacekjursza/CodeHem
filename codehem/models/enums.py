"""
Core data models for the CodeHem code manipulation library.
"""
from enum import Enum

class CodeElementType(str, Enum):
    """Types of code elements that can be identified and manipulated"""
    CLASS = 'class'
    METHOD = 'method'
    FUNCTION = 'function'
    PROPERTY = 'property'
    PROPERTY_GETTER = 'property_getter'
    PROPERTY_SETTER = 'property_setter'
    STATIC_PROPERTY = 'static_property'
    IMPORT = 'import'
    MODULE = 'module'
    VARIABLE = 'variable'
    PARAMETER = 'parameter'
    RETURN_VALUE = 'return_value'
    META_ELEMENT = 'meta_element'
    INTERFACE = 'interface'
    DECORATOR = 'decorator'
    ANNOTATION = 'annotation'
    ATTRIBUTE = 'attribute'
    DOC_COMMENT = 'doc_comment'
    TYPE_HINT = 'type_hint'
    FILE = 'file'
    DOCSTRING = 'docstring'
    # TypeScript-specific element types
    TYPE_ALIAS = 'type_alias'
    ENUM = 'enum'
    NAMESPACE = 'namespace'
    UNKNOWN = 'unknown'