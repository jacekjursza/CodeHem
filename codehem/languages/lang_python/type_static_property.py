from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler

class PythonStaticPropertyHandler(LanguageHandler):
    """Handler for Python static property elements."""
    language_code = 'python'
    element_type = CodeElementType.STATIC_PROPERTY
    tree_sitter_query = """
    (class_definition
      body: (block 
        (expression_statement 
          (assignment 
            left: (identifier) @prop_name)))) @static_prop_def
    """
    regexp_pattern = r'(?:^|\n)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^()\n]+)(?:\n|$)'
    custom_extract = False