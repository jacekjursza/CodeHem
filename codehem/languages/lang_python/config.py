"""
Language-specific configuration for Python in CodeHem.
"""
from codehem.models.enums import CodeElementType
from .python_post_processor import PythonExtractionPostProcessor

# Define a specific Tree-sitter query for Python imports
_PY_IMPORT_QUERY = """
(import_statement) @import_simple
(import_from_statement) @import_from
"""
# Simplified Python property/method queries (v5) - Minimal valid structure
_PY_METHOD_QUERY = "(function_definition name: (identifier) @method_name) @method_def"
_PY_FUNC_QUERY = "(function_definition name: (identifier) @function_name) @function_def"
# Capture decorated definition; extractor must check decorator content
_PY_GETTER_QUERY = "(decorated_definition) @getter_def"
_PY_SETTER_QUERY = "(decorated_definition) @setter_def"
# Corrected Static Property Query (v6) - Use list for alternatives within class body block
_PY_STATIC_PROP_QUERY = """
(class_definition
    body: (block [
        (assignment left: (identifier) @static_prop_name value: (_) @value) @assignment
        (typed_assignment left: (identifier) @static_prop_name type: (_) @type value: (_) @value) @typed_assignment
        (expression_statement (assignment left: (identifier) @static_prop_name value: (_) @value)) @expr_assignment
    ])
)
"""
_PY_DECORATOR_QUERY = "(decorator) @decorator_node"
_PY_CLASS_QUERY = "(class_definition name: (identifier) @class_name) @class_def"

# Provide only necessary keys for placeholders, primarily 'tree_sitter_query' to override base templates
PYTHON_PLACEHOLDERS = {
    CodeElementType.CLASS:           {'tree_sitter_query': _PY_CLASS_QUERY},
    CodeElementType.METHOD:          {'tree_sitter_query': _PY_METHOD_QUERY},
    CodeElementType.FUNCTION:        {'tree_sitter_query': _PY_FUNC_QUERY},
    CodeElementType.IMPORT:          {'tree_sitter_query': _PY_IMPORT_QUERY, 'custom_extract': True},
    CodeElementType.PROPERTY_GETTER: {'tree_sitter_query': _PY_GETTER_QUERY},
    CodeElementType.PROPERTY_SETTER: {'tree_sitter_query': _PY_SETTER_QUERY},
    CodeElementType.STATIC_PROPERTY: {'tree_sitter_query': _PY_STATIC_PROP_QUERY},
    CodeElementType.DECORATOR:       {'tree_sitter_query': _PY_DECORATOR_QUERY}
    # Regex patterns are removed here as TS query should be primary
}

LANGUAGE_CONFIG = {
    'language_code': 'python',
    'post_processor_class': PythonExtractionPostProcessor,
    'template_placeholders': PYTHON_PLACEHOLDERS
}