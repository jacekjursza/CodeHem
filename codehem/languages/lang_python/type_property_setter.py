from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

class PythonPropertySetterHandler(LanguageHandler):
    """Handler for Python property setter elements."""
    language_code = 'python'
    element_type = CodeElementType.PROPERTY_SETTER
    tree_sitter_query = """
    (decorated_definition
      decorator: (decorator 
        name: (attribute
          object: (identifier) @prop_obj
          attribute: (identifier) @decorator_attr (#eq? @decorator_attr "setter")))
      definition: (function_definition
        name: (identifier) @property_name)) @property_setter_def
    """
    regexp_pattern = r'@([a-zA-Z_][a-zA-Z0-9_]*).setter\s*\n\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*self[^)]*\)(?:\s*->.*?)?\s*:(.*?)(?=\n(?:\s+@|\s+def|\Z))'
    custom_extract = False