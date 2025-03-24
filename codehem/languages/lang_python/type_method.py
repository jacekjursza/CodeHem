"""Handler for Python method elements."""
from codehem.core.registry import handler
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

@handler
class PythonMethodHandler(LanguageHandler):
    """Handler for Python method elements."""
    language_code = 'python'
    element_type = CodeElementType.METHOD
    tree_sitter_query = "(function_definition name: (identifier) @method_name parameters: (parameters (identifier) @first_param (#eq? @first_param \"self\")) body: (block) @body) @method_def"
    regexp_pattern = 'def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(\\s*self[^)]*\\)(?:\\s*->.*?)?\\s*:(.*?)(?=\\n(?:\\s+@|\\s+def|\\s*class|\\Z))'
    custom_extract = False
