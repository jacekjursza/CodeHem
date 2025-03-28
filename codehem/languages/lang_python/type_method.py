"""Handler for Python method elements."""
from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType


@element_type_descriptor
class PythonMethodHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python method elements."""
    language_code = 'python'
    element_type = CodeElementType.METHOD
    tree_sitter_query = '\n    (function_definition\n    name: (identifier) @method_name\n    parameters: (parameters (identifier) @first_param (#eq? @first_param "self"))\n    body: (block) @body) @method_def\n    (decorated_definition\n    (decorator) @decorator\n    definition: (function_definition\n    name: (identifier) @method_name\n    parameters: (parameters (identifier) @first_param (#eq? @first_param "self"))\n    body: (block) @body)) @decorated_method_def\n    '
    # Updated regex to match only the method signature, not the entire body
    regexp_pattern = 'def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(\\s*self[^)]*\\)(?:\\s*->.*?)?\\s*:'
    custom_extract = False
