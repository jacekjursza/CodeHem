import logging
from typing import Optional
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

@element_type_descriptor
class TypeScriptStaticPropertyHandlerElementType(ElementTypeLanguageDescriptor):
    """ Handler descriptor for TypeScript/JavaScript static property elements. """
    _LANGUAGE: str = 'typescript'
    _TYPE: CodeElementType = CodeElementType.STATIC_PROPERTY
    language_code: str = _LANGUAGE
    element_type: CodeElementType = _TYPE
    tree_sitter_query: Optional[str] = None
    regexp_pattern: Optional[str] = None
    custom_extract: bool = False