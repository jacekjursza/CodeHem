"""Handler for Python function elements."""
from codehem.core.registry import element_type_descriptor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor

@element_type_descriptor
class PythonFunctionHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python function elements."""
    language_code = 'python'
    element_type = CodeElementType.FUNCTION
    tree_sitter_query = '\n    (function_definition\n      name: (identifier) @function_name\n      parameters: (parameters) @params\n      body: (block) @body) @function_def\n    '
    # Update regex to stop at the end of the indented block, not at the next function/class or end-of-file
    regexp_pattern = 'def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\((?!.*?self)[^)]*\\)(?:\\s*->.*?)?\\s*:'
    custom_extract = False
