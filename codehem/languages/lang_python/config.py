# Stored in memory from previous analysis
"""
Language-specific configuration for Python in CodeHem.
"""
from codehem.models.enums import CodeElementType

# *** CHANGE START ***
# Import moved post-processor
from .python_post_processor import PythonExtractionPostProcessor



# Define placeholders nested by CodeElementType for clarity and easier lookup
PYTHON_PLACEHOLDERS = {
    CodeElementType.CLASS: {
        'CLASS_NODE': 'class_definition',
        'NAME_NODE': 'identifier',
        'BODY_NODE': 'block',
        'CLASS_PATTERN': 'class',
        'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
        'INHERITANCE_PATTERN': '\\s*\\([^)]*\\)',
        'BODY_START': ':'
    },
    CodeElementType.METHOD: {
        'NAME_NODE': 'identifier',
        'FIRST_PARAM_ID': 'self', # Or 'cls' could be handled in extractor logic
        'METHOD_PATTERN': 'def',
        'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
        'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
        'BODY_START': ':'
    },
    CodeElementType.FUNCTION: {
        'NAME_NODE': 'identifier',
        'FUNCTION_PATTERN': 'def',
        'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
        'PARAMS_PATTERN': '(?!self\\s*[,)])[^)]*', # Exclude 'self'/'cls' - might need refinement
        'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
        'BODY_START': ':'
    },
    CodeElementType.IMPORT: {
        # Note: Import query likely complex and defined directly in template
        'IMPORT_PATTERN': '(?:^|\\n)\\s*(import\\s+(?:[a-zA-Z0-9_.,\\s*()]+)|from\\s+[a-zA-Z0-9_.]+\\s+import\\s+(?:[a-zA-Z0-9_.,\\s*()]+))'
    },
    CodeElementType.PROPERTY_GETTER: {
        'NAME_NODE': 'identifier',
        'GETTER_DECORATOR_ID': 'property', # Used in tree-sitter #eq? predicate
        'GETTER_DECORATOR_PATTERN': '@property', # Used in regex
        'METHOD_PATTERN': 'def',
        'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
        'FIRST_PARAM_PATTERN': 'self',
        'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
        'BODY_CAPTURE_LOOKAHEAD': '(.*?)(?=\\n(?:[ \\t]*@|[ \\t]*def|\\Z))' # Regex lookahead
    },
    CodeElementType.PROPERTY_SETTER: {
        'NAME_NODE': 'identifier',
        'SETTER_DECORATOR_ATTR': 'setter', # Used in tree-sitter #eq? predicate
        'PROPERTY_NAME_PATTERN': '([a-zA-Z_][a-zA-Z0-9_]*)', # Regex for @{prop_name}.setter
        'SETTER_ATTR_PATTERN': 'setter', # Regex attribute name
        'METHOD_PATTERN': 'def',
        'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
        'FIRST_PARAM_PATTERN': 'self',
        'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
        'BODY_CAPTURE_LOOKAHEAD': '(.*?)(?=\\n(?:[ \\t]*@|[ \\t]*def|\\Z))' # Regex lookahead
    },
    CodeElementType.STATIC_PROPERTY: {
        # Primarily relies on tree-sitter query finding assignments in class block
        'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*', # Regex fallback parts
        'OPTIONAL_NEWLINE_INDENT': '(?:^|\\n)\\s+',
        'OPTIONAL_TYPE_HINT': '(?:\\s*:\\s*[^=]+?)?',
        'VALUE_CAPTURE': '.+?',
        'OPTIONAL_COMMENT_ENDLINE': '(?:$|\\s*#)'
    },
    CodeElementType.DECORATOR: {
        'DECORATOR_PREFIX': '@',
        'QUALIFIED_NAME_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*(?:\\.[a-zA-Z_][a-zA-Z0-9_]*)*',
        'ARGS_PATTERN': '\\([^)]*\\)' # Optional arguments part
    }
    # Add other types as needed (e.g., INTERFACE, TYPE_ALIAS if supported in Python via typing)
}

# Configuration dictionary for the Python language service
# Registry will load this.
LANGUAGE_CONFIG = {
    'language_code': 'python',
    'post_processor_class': PythonExtractionPostProcessor,
    # Formatter is now associated directly in LanguageService init if needed,
    # but registry could load it from here too if desired.
    # 'formatter_class': PythonFormatter,
    'template_placeholders': PYTHON_PLACEHOLDERS
}