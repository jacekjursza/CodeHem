import logging
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType
# We don't call create_element_type_descriptor here to avoid circular imports
# The patterns will be loaded dynamically by the LanguageService or Extractor

logger = logging.getLogger(__name__)

@element_type_descriptor
class TypeScriptImportHandlerElementType(ElementTypeLanguageDescriptor):
    """ Handler descriptor for TypeScript/JavaScript import elements. """
    language_code: str = 'typescript'
    element_type: CodeElementType = CodeElementType.IMPORT
    # Set patterns to None initially; they should be populated from config later
    tree_sitter_query: str | None = None
    regexp_pattern: str | None = None
    # Import extractor usually combines results, so maybe custom_extract=True is appropriate
    # Let's stick to False for now and let the ImportExtractor class handle combination logic.
    custom_extract: bool = False

    def __init__(self):
        # Initialize base class attributes correctly
        super().__init__(
            language_code=self.language_code,
            element_type=self.element_type,
            tree_sitter_query=self.tree_sitter_query,
            regexp_pattern=self.regexp_pattern,
            custom_extract=self.custom_extract
        )
        logger.debug(f"Initialized {self.__class__.__name__}")
        # In a more robust implementation, patterns might be loaded here or lazily