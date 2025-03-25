import re
from typing import Optional, Tuple
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import element_type_descriptor

@element_type_descriptor
class PythonClassHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python class elements."""
    language_code = 'python'
    element_type = CodeElementType.CLASS
    tree_sitter_query = '\n    (class_definition\n      name: (identifier) @class_name\n      body: (block) @body) @class_def\n    '
    regexp_pattern = 'class\\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:\\s*\\([^)]*\\))?\\s*:(.*?)(?=\\n(?:class|def|\\Z))'
    custom_extract = False
