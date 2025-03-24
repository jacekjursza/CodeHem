"""Handler for Python function elements."""
from codehem.core.registry import handler
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

@handler
class PythonFunctionHandler(LanguageHandler):
    """Handler for Python function elements."""
    language_code = 'python'
    element_type = CodeElementType.FUNCTION
    tree_sitter_query = """
    (function_definition
      name: (identifier) @function_name
      parameters: (parameters) @params
      body: (block) @body) @function_def
    """
    regexp_pattern = 'def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\((?!.*?self)[^)]*\\)(?:\\s*->.*?)?\\s*:(.*?)(?=\\n(?:def|class)|$)'
    custom_extract = False