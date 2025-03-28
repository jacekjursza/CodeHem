"""Handler for Python import elements."""
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType


@element_type_descriptor
class PythonImportHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python import elements."""
    language_code = 'python'
    element_type = CodeElementType.IMPORT
    tree_sitter_query = '''
    (import_statement) @import
    (import_from_statement) @import_from
    '''
    # Simplified regex pattern for better matching
    regexp_pattern = '(import\\s+[^\\n;]+|from\\s+[^\\n;]+\\s+import\\s+[^\\n;]+)'
    custom_extract = False