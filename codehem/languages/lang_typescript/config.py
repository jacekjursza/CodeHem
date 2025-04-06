"""
Language-specific configuration for TypeScript/JavaScript in CodeHem.
"""
from codehem.models.enums import CodeElementType
from .typescript_post_processor import TypeScriptExtractionPostProcessor
from .formatting.typescript_formatter import TypeScriptFormatter

# Basic patterns for TS/JS, can be refined
_IDENTIFIER = r"[a-zA-Z_$][a-zA-Z0-9_$]*"
_PARAMS = r"[^)]*" # Simplified parameter pattern
_TYPE_ANNOTATION = r"(?:\s*:\s*[\w.<>\[\]|&]+(?:\s*=\s*[^,\]\)]+)?)" # Type annotation, possibly with default
_RETURN_TYPE = r"(?:\s*:\s*[\w.<>\[\]|&]+)" # Return type annotation
_OPTIONAL_ASYNC = r"(?:async\s+)?"
_OPTIONAL_ACCESS = r"(?:(?:public|private|protected|static|readonly)\s+)*"
_BODY_START = r"{"
_DECORATOR = r"@" + _IDENTIFIER + r"(?:\([^)]*\))?"

# Placeholders for TreeSitter queries and Regex patterns
# Node names are specific to the tree-sitter-typescript grammar.
TS_PLACEHOLDERS = {
    CodeElementType.CLASS: {
        'CLASS_NODE': 'class_declaration',
        'NAME_NODE': 'type_identifier',
        'BODY_NODE': 'class_body',
        'CLASS_PATTERN': 'class',
        'IDENTIFIER_PATTERN': _IDENTIFIER,
        'INHERITANCE_PATTERN': r"(?:\s+(?:extends|implements)\s+[\w.,\s<>]+)",
        'BODY_START': _BODY_START
    },
    CodeElementType.INTERFACE: {
        'INTERFACE_NODE': 'interface_declaration',
        'NAME_NODE': 'type_identifier',
        'BODY_NODE': 'object_type',
        'INTERFACE_PATTERN': 'interface',
        'IDENTIFIER_PATTERN': _IDENTIFIER,
        'EXTENDS_PATTERN': r"(?:\s+extends\s+[\w.,\s<>]+)",
        'BODY_START': _BODY_START
    },
    CodeElementType.METHOD: {
        'METHOD_NODE': 'method_definition',
        'NAME_NODE': 'property_identifier',
        'PARAMS_NODE': 'formal_parameters',
        'RETURN_TYPE_NODE': 'type_annotation',
        'BODY_NODE': 'statement_block',
        'METHOD_PATTERN': _OPTIONAL_ACCESS + _OPTIONAL_ASYNC + _IDENTIFIER + r"\s*\(" + _PARAMS + r"\)" + _RETURN_TYPE + r"?\s*" + _BODY_START,
        'IDENTIFIER_PATTERN': _IDENTIFIER,
    },
    CodeElementType.FUNCTION: {
        'FUNCTION_NODE': 'function_declaration', # Or 'function'/'arrow_function'
        'NAME_NODE': 'identifier',
        'PARAMS_NODE': 'formal_parameters',
        'RETURN_TYPE_NODE': 'type_annotation',
        'BODY_NODE': 'statement_block',
        'FUNCTION_PATTERN': _OPTIONAL_ASYNC + r"function\s+" + _IDENTIFIER + r"\s*\(" + _PARAMS + r"\)" + _RETURN_TYPE + r"?\s*" + _BODY_START,
        'ARROW_FUNCTION_PATTERN': _OPTIONAL_ACCESS + _OPTIONAL_ASYNC + r"\(" + _PARAMS + r"\)\s*" + _RETURN_TYPE + r"?\s*=>",
        'IDENTIFIER_PATTERN': _IDENTIFIER,
    },
    CodeElementType.IMPORT: {
        # --- CORRECTED TreeSitter Query ---
        # Capture the entire import statement
        'IMPORT_NODE': 'import_statement', # Base node for imports
        'tree_sitter_query': '(import_statement) @import', # Simplified query
        # Regex fallback (less reliable)
        'IMPORT_PATTERN': r"(?:^|\n)\s*import(?:[""'\s{}.*a-zA-Z0-9_$*\-,]+from\s+)?[""'][^""']+[""'];?",
    },
    CodeElementType.PROPERTY: {
        'PROPERTY_NODE': 'public_field_definition',
        'NAME_NODE': 'property_identifier',
        'TYPE_NODE': 'type_annotation',
        'VALUE_NODE': 'expression',
        'PROPERTY_PATTERN': _OPTIONAL_ACCESS + _IDENTIFIER + _TYPE_ANNOTATION + r"?\s*(?:=\s*[^;]+)?\s*;?",
        'IDENTIFIER_PATTERN': _IDENTIFIER,
    },
    CodeElementType.DECORATOR: {
        'DECORATOR_NODE': 'decorator',
        'DECORATOR_CALL_NODE': 'call_expression',
        'DECORATOR_NAME_NODE': 'identifier', # Or member_expression
        'DECORATOR_PATTERN': _DECORATOR,
        'IDENTIFIER_PATTERN': _IDENTIFIER,
    },
    CodeElementType.TYPE_ALIAS: {
        'TYPE_ALIAS_NODE': 'type_alias_declaration',
        'NAME_NODE': 'type_identifier',
        'TYPE_NODE': 'type',
        'TYPE_ALIAS_PATTERN': r"type\s+" + _IDENTIFIER + r"\s*=\s*[^;]+;?",
        'IDENTIFIER_PATTERN': _IDENTIFIER,
    },
    # Define placeholders for PROPERTY_GETTER, PROPERTY_SETTER, STATIC_PROPERTY, ENUM etc. as needed
    # These often involve specific combinations of keywords, decorators, and node types.
    CodeElementType.PROPERTY_GETTER: {
        'GETTER_NODE': 'method_definition', # Often represented as method def
        'GET_KEYWORD': 'get', # Look for 'get' keyword
        'NAME_NODE': 'property_identifier',
        # TreeSitter query would look for method_definition starting with 'get'
        'tree_sitter_query': '(method_definition (get) name: (property_identifier) @getter_name) @getter_def',
    },
     CodeElementType.PROPERTY_SETTER: {
        'SETTER_NODE': 'method_definition',
        'SET_KEYWORD': 'set',
        'NAME_NODE': 'property_identifier',
        'PARAMS_NODE': 'formal_parameters',
         # TreeSitter query would look for method_definition starting with 'set'
        'tree_sitter_query': '(method_definition (set) name: (property_identifier) @setter_name) @setter_def',
    },
     CodeElementType.STATIC_PROPERTY: {
         'STATIC_PROP_NODE': 'public_field_definition', # May vary based on access modifier
         'STATIC_KEYWORD': 'static',
         'NAME_NODE': 'property_identifier',
         'tree_sitter_query': '(public_field_definition (static) name: (property_identifier) @static_prop_name) @static_prop_def', # Example query, needs validation
     },
}

# Main configuration dictionary for the language
LANGUAGE_CONFIG = {
    'language_code': 'typescript',
    'formatter_class': TypeScriptFormatter,
    'post_processor_class': TypeScriptExtractionPostProcessor,
    'template_placeholders': TS_PLACEHOLDERS,
}