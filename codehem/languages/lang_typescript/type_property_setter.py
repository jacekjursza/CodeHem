# New file: d:\code\codehem\codehem\languages\lang_typescript\type_property_setter.py
import logging
from typing import Optional
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

@element_type_descriptor
class TypeScriptPropertySetterHandlerElementType(ElementTypeLanguageDescriptor):
    """ Handler descriptor for TypeScript setter property elements. """
    _LANGUAGE: str = 'typescript'
    _TYPE: CodeElementType = CodeElementType.PROPERTY_SETTER
    language_code: str = _LANGUAGE
    element_type: CodeElementType = _TYPE
    tree_sitter_query: Optional[str] = None
    regexp_pattern: Optional[str] = None
    custom_extract: bool = False