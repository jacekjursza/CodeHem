from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType


@element_type_descriptor
class PythonPropertyGetterHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python property getter elements."""
    language_code = 'python'
    element_type = CodeElementType.PROPERTY_GETTER
    tree_sitter_query = '(decorated_definition (decorator (identifier) @decorator_name) (function_definition name: (identifier) @property_name)) @property_def (#eq? @decorator_name "property")'
    regexp_pattern = '@property\\s*\\n\\s*def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(\\s*self[^)]*\\)(?:\\s*->.*?)?\\s*:(.*?)(?=\\n(?:\\s+@|\\s+def|\\Z))'
    custom_extract = False
