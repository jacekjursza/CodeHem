from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType


@element_type_descriptor
class PythonClassHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python class elements."""
    language_code = 'python'
    element_type = CodeElementType.CLASS
    # Fixed tree-sitter query to properly match Python classes
    tree_sitter_query = """
    (class_definition
      name: (identifier) @class_name
      body: (block) @body) @class_def
    """
    # Fixed regex to properly match Python classes
    regexp_pattern = 'class\\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\\s*\\([^)]*\\))?\\s*:'
    custom_extract = False