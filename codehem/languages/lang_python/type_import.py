"""Handler for Python import elements."""
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

class PythonImportHandler(LanguageHandler):
    """Handler for Python import elements."""
    language_code = 'python'
    element_type = CodeElementType.IMPORT
    tree_sitter_query = """
    (import_statement) @import
    (import_from_statement) @import_from
    """
    regexp_pattern = '(?:import\\s+([a-zA-Z_][a-zA-Z0-9_.*]+)(?:\\s+as\\s+[a-zA-Z_][a-zA-Z0-9_]*)?|from\\s+([a-zA-Z_][a-zA-Z0-9_.*]+)\\s+import\\s+(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\\s+as\\s+[a-zA-Z_][a-zA-Z0-9_]*)?(?:\\s*,\\s*[a-zA-Z_][a-zA-Z0-9_]*(?:\\s+as\\s+[a-zA-Z_][a-zA-Z0-9_]*)?)*|\\*))'
    custom_extract = False