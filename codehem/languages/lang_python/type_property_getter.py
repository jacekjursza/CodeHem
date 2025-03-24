from codehem.languages.registry import handler
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

@handler
class PythonPropertyGetterHandler(LanguageHandler):
    """Handler for Python property getter elements."""
    language_code = 'python'
    element_type = CodeElementType.PROPERTY_GETTER
    tree_sitter_query = """
    (decorated_definition
      decorator: (decorator 
        name: (identifier) @decorator_name (#eq? @decorator_name "property"))
      definition: (function_definition
        name: (identifier) @property_name)) @property_def
    """
    regexp_pattern = r'@property\s*\n\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*self[^)]*\)(?:\s*->.*?)?\s*:(.*?)(?=\n(?:\s+@|\s+def|\Z))'
    custom_extract = False