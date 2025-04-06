import logging
import sys
# --- Debug Print Added ---
print(f"--- Executing {__name__} ---")
# --- End Debug Print ---
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_template import create_element_type_descriptor

logger = logging.getLogger(__name__)

@element_type_descriptor
class PythonFunctionHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python function elements, using templates."""
    # Define language and type for this specific handler
    _LANGUAGE = 'python'
    _TYPE = CodeElementType.FUNCTION

    # --- Dynamic generation ---
    _attrs = create_element_type_descriptor(_LANGUAGE, _TYPE)
    # ---

    # --- Assign attributes, falling back if generation failed ---
    language_code = _LANGUAGE
    element_type = _TYPE

    if _attrs:
        # Successfully generated attributes from template
        tree_sitter_query = _attrs.get('tree_sitter_query')
        regexp_pattern = _attrs.get('regexp_pattern')
        # Use generated custom_extract value, default to False if missing in template result
        custom_extract = _attrs.get('custom_extract', False)
    else:
        # Failed to generate attributes from template
        logger.error(f'Could not generate descriptor attributes for {_LANGUAGE}/{_TYPE.value} from template. Check template definitions and placeholders.')
        tree_sitter_query = None
        regexp_pattern = None
        custom_extract = False