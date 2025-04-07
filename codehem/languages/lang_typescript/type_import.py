# Content of codehem\languages\lang_typescript\type_import.py
import logging
from typing import Optional # Added Optional
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
logger = logging.getLogger(__name__)

@element_type_descriptor
class TypeScriptImportHandlerElementType(ElementTypeLanguageDescriptor):
    """ Handler descriptor for TypeScript/JavaScript import elements. """
    # Define constants for registration and identification
    _LANGUAGE: str = 'typescript'
    _TYPE: CodeElementType = CodeElementType.IMPORT

    # Set identifying attributes for the instance
    language_code: str = _LANGUAGE
    element_type: CodeElementType = _TYPE

    # Initialize pattern fields to None - they will be populated by initialize_patterns()
    tree_sitter_query: Optional[str] = None
    regexp_pattern: Optional[str] = None
    # Set custom_extract based on typical import behavior
    custom_extract: bool = True # Usually True for imports to handle consolidation

    # __init__ is no longer needed here