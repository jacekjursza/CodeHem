import logging
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

@element_type_descriptor
class TypeScriptInterfaceHandlerElementType(ElementTypeLanguageDescriptor):
    """ Handler descriptor for TypeScript interface elements. """
    language_code: str = 'typescript'
    element_type: CodeElementType = CodeElementType.INTERFACE
    # Patterns are loaded dynamically from config by the extractor/service
    tree_sitter_query: str | None = None
    regexp_pattern: str | None = None
    custom_extract: bool = False # Use pattern-based extraction

    def __init__(self):
        super().__init__(
            language_code=self.language_code,
            element_type=self.element_type,
            tree_sitter_query=self.tree_sitter_query,
            regexp_pattern=self.regexp_pattern,
            custom_extract=self.custom_extract
        )
        logger.debug(f"Initialized {self.__class__.__name__}")