# Content of codehem\languages\lang_typescript\type_interface.py
import logging
from typing import Optional # Added Optional
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
logger = logging.getLogger(__name__)

@element_type_descriptor
class TypeScriptInterfaceHandlerElementType(ElementTypeLanguageDescriptor):
    """ Handler descriptor for TypeScript interface elements. """
    # Define constants for registration and identification
    _LANGUAGE: str = 'typescript'
    _TYPE: CodeElementType = CodeElementType.INTERFACE

    # Set identifying attributes for the instance
    language_code: str = _LANGUAGE
    element_type: CodeElementType = _TYPE

    # Initialize pattern fields to None - they will be populated by initialize_patterns()
    tree_sitter_query: Optional[str] = None
    regexp_pattern: Optional[str] = None
    custom_extract: bool = False # Default unless template overrides during init

    # __init__ is no longer needed here