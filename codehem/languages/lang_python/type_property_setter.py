from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType


@element_type_descriptor
class PythonPropertySetterHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python property setter elements."""
    language_code = 'python'
    element_type = CodeElementType.PROPERTY_SETTER
    tree_sitter_query = '(decorated_definition (decorator (attribute object: (identifier) @prop_obj attribute: (identifier) @decorator_attr)) (function_definition name: (identifier) @property_name)) @property_setter_def (#eq? @decorator_attr "setter")'
    regexp_pattern = '@([a-zA-Z_][a-zA-Z0-9_]*).setter\\s*\\n\\s*def\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\(\\s*self[^)]*\\)(?:\\s*->.*?)?\\s*:(.*?)(?=\\n(?:\\s+@|\\s+def|\\Z))'
    custom_extract = False
