# Content of codehem\languages\lang_python\type_class.py
import logging
from typing import Optional # Added Optional
# Removed: import sys - Not used
print(f'--- Executing {__name__} ---')
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
logger = logging.getLogger(__name__)

@element_type_descriptor
class PythonClassHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler descriptor for Python class elements."""
    # Define constants for registration and identification
    _LANGUAGE = 'python'
    _TYPE = CodeElementType.CLASS

    # Set identifying attributes for the instance
    language_code: str = _LANGUAGE
    element_type: CodeElementType = _TYPE

    # Initialize pattern fields to None - they will be populated by initialize_patterns()
    tree_sitter_query: Optional[str] = None
    regexp_pattern: Optional[str] = None
    custom_extract: bool = False # Default unless template overrides during init

    # --- Removed class-level pattern initialization ---
    # _attrs = create_element_type_descriptor(_LANGUAGE, _TYPE) # REMOVED
    # if _attrs: ... block removed
    # else: ... block removed
    # --- End Removed Block ---