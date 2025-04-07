# d:\code\codehem\codehem\languages\lang_typescript\config.py
# Revised version based on test_ts2.py analysis

"""
Language-specific configuration for TypeScript/JavaScript in CodeHem.
(Combined Corrected Queries, Capture Names, and Placeholders)
"""
from codehem.models.enums import CodeElementType
from .typescript_post_processor import TypeScriptExtractionPostProcessor
from .formatting.typescript_formatter import TypeScriptFormatter

# --- Tree-sitter Query Definitions ---

# Imports - Query seems to find nodes; potential issue in extractor/post-processor logic
_TS_IMPORT_QUERY = """
(import_statement) @import_statement
"""

# Functions (Declarations & Arrow) - Appeared OK in query tests
_TS_FUNCTION_QUERY = """
(function_declaration
  name: (identifier) @function_name
  parameters: (formal_parameters) @params
  return_type: (type_annotation)? @return_type
  body: (statement_block) @body
) @function_def

(export_statement
  declaration: (function_declaration
    name: (identifier) @function_name
    parameters: (formal_parameters) @params
    return_type: (type_annotation)? @return_type
    body: (statement_block) @body
  ) @function_def_exported
)

(lexical_declaration
  (variable_declarator
    name: (identifier) @function_name
    value: (arrow_function
      parameters: (_) @params
      return_type: (type_annotation)? @return_type
      body: (_) @arrow_func_body
    )
  )
) @arrow_function_def

(export_statement
  declaration: (lexical_declaration
    (variable_declarator
      name: (identifier) @function_name
      value: (arrow_function
        parameters: (_) @params
        return_type: (type_annotation)? @return_type
        body: (_) @arrow_func_body
      )
    )
  ) @arrow_function_def_exported
)
"""

# Interfaces - Query with 'interface_body' seems correct based on provided AST
_TS_INTERFACE_QUERY = """
(interface_declaration
  name: (type_identifier) @interface_name
  body: (interface_body) @interface_body
) @interface_def

(export_statement
  declaration: (interface_declaration
    name: (type_identifier) @interface_name
    body: (interface_body) @interface_body
  ) @interface_def_exported
)
"""

# Classes - Appeared OK in query tests
_TS_CLASS_QUERY = """
(class_declaration
  name: (type_identifier) @class_name
  body: (class_body) @class_body
) @class_def

(export_statement
  declaration: (class_declaration
    name: (type_identifier) @class_name
    body: (class_body) @class_body
  ) @class_def_exported
)
"""

# Methods / Getters / Setters - REVISED (Removed invalid predicates, capture modifiers as children)
_TS_METHOD_QUERY = """
(method_definition
  ;; Capture modifiers as simple child nodes if needed by logic later
  (accessibility_modifier)? @accessibility
  (static)? @static_modifier
  (readonly)? @readonly_modifier
  (async)? @async_modifier

  ;; These are OK - 'kind' is a named field in the grammar
  kind: (get)? @getter_kind
  kind: (set)? @setter_kind

  name: (property_identifier) @method_name
  parameters: (formal_parameters) @params
  return_type: (type_annotation)? @return_type
  body: (statement_block)? @body
) @method_def
"""

# Properties (Class Fields / Interface Signatures) - REVISED
_TS_PROPERTY_QUERY = """
(public_field_definition ;; Type from AST for class fields
  ;; Capture modifiers as children
  (accessibility_modifier)? @accessibility
  (static)? @static_modifier
  (readonly)? @readonly_modifier

  name: (property_identifier) @property_name
  type: (type_annotation)? @type
  value: (_)? @value ;; Capture optional initial value
) @property_def

;; For properties within interfaces
(property_signature
  (readonly)? @readonly ;; This predicate might be valid here
  name: (property_identifier) @property_name
  (question_mark)? @optional
  type: (type_annotation)? @type
) @interface_property_def
"""

# Decorators - REVISED (Removed invalid 'expression:' field)
_TS_DECORATOR_QUERY = """
(decorator
   ;; Capture the node right after '@'
   ;; Usually a 'call_expression' or 'identifier'
   (_) @decorator_expression
) @decorator_node
"""

# Type Aliases - Appeared OK
_TS_TYPE_ALIAS_QUERY = """
(type_alias_declaration
  name: (type_identifier) @type_name
  value: (_) @type_value
) @type_alias_def

(export_statement
  declaration: (type_alias_declaration
    name: (type_identifier) @type_name
    value: (_) @type_value
  ) @type_alias_def_exported
)
"""

# Enums - Appeared OK
_TS_ENUM_QUERY = """
(enum_declaration
  name: (identifier) @enum_name
  body: (enum_body) @enum_body
) @enum_def

(export_statement
  declaration: (enum_declaration
    name: (identifier) @enum_name
    body: (enum_body) @enum_body
  ) @enum_def_exported
)
"""

# Namespaces / Modules - Appeared OK
_TS_NAMESPACE_QUERY = """
(module
  name: [
    (identifier) @namespace_name
    (string) @namespace_name_string
  ] @namespace_name_capture
  body: (module_body | statement_block)? @namespace_body
) @namespace_def

(export_statement
  declaration: (module
    name: [ (identifier) @namespace_name (string) @namespace_name_string ] @namespace_name_capture
    body: (module_body | statement_block)? @namespace_body
  ) @namespace_def_exported
)

(ambient_declaration
  (module
     name: [ (identifier) @namespace_name (string) @namespace_name_string ] @namespace_name_capture
     body: (module_body | statement_block)? @namespace_body
  )
) @ambient_namespace_def
"""

# --- Regex Placeholder Definitions (simplified, primarily for reference) ---
_IDENTIFIER = '[a-zA-Z_$][a-zA-Z0-9_$]*'
_PARAMS = '[^)]*'
_TYPE_ANNOTATION = '(?:\\s*:\\s*[\\w.<>\\[\\]|&\\s\'"{}()=>]+)?'
_RETURN_TYPE = '(?:\\s*:\\s*[\\w.<>\\[\\]|&\\s\'"{}()=>]+)'
_OPTIONAL_ASYNC = '(?:async\\s+)?'
_OPTIONAL_ACCESS = '(?:(?:public|private|protected|static|readonly)\\s+)*'
_BODY_START = '{'
_DECORATOR_REGEX = '@' + _IDENTIFIER + '(?:\\([^)]*\\))?'
_INHERITANCE = '(?:\\s+(?:extends|implements)\\s+[\\w.,\\s<>]+)?'
_FIRST_PARAM = '(?:this|' + _IDENTIFIER + ')'
_VALUE_CAPTURE = '.+?'
_OPTIONAL_COMMENT_ENDLINE = '(?:$|\\s*//|\\s*/\\*)'

# --- Mapping Element Types to Queries and Placeholders ---
TS_PLACEHOLDERS = {
    CodeElementType.CLASS: {
        'tree_sitter_query': _TS_CLASS_QUERY,
        'CLASS_NODE': 'class_declaration', 'NAME_NODE': 'type_identifier', 'BODY_NODE': 'class_body',
        'CLASS_PATTERN': '(?:export\\s+)?(?:abstract\\s+)?class', 'IDENTIFIER_PATTERN': _IDENTIFIER,
        'INHERITANCE_PATTERN': _INHERITANCE, 'BODY_START': _BODY_START
    },
    CodeElementType.INTERFACE: {
        'tree_sitter_query': _TS_INTERFACE_QUERY, # Uses interface_body
        'INTERFACE_NODE': 'interface_declaration', 'NAME_NODE': 'type_identifier', 'BODY_NODE': 'interface_body',
        'INTERFACE_PATTERN': '(?:export\\s+)?interface', 'IDENTIFIER_PATTERN': _IDENTIFIER,
        'EXTENDS_PATTERN': '(?:\\s+extends\\s+[\\w.,\\s<>]+)?', 'BODY_START': _BODY_START
    },
    CodeElementType.METHOD: {
        'tree_sitter_query': _TS_METHOD_QUERY, # Uses REVISED query
        'NAME_NODE': 'property_identifier', 'FIRST_PARAM_ID': 'this',
        'METHOD_PATTERN': _OPTIONAL_ACCESS + _OPTIONAL_ASYNC + _IDENTIFIER, 'IDENTIFIER_PATTERN': _IDENTIFIER,
        'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?', 'BODY_START': _BODY_START
    },
    CodeElementType.FUNCTION: {
        'tree_sitter_query': _TS_FUNCTION_QUERY,
        'NAME_NODE': 'identifier', 'PARAMS_NODE': 'formal_parameters', 'RETURN_TYPE_NODE': 'type_annotation', 'BODY_NODE': 'statement_block',
        'FUNCTION_PATTERN': '(?:export\\s+)?' + _OPTIONAL_ASYNC + 'function', 'IDENTIFIER_PATTERN': _IDENTIFIER,
        'PARAMS_PATTERN': _PARAMS, 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?', 'BODY_START': _BODY_START,
        'ARROW_FUNCTION_PATTERN': '(?:export\\s+)?(?:const|let)\\s+' + _IDENTIFIER + '\\s*[:]?.*=\\s*' + _OPTIONAL_ASYNC + '\\(?' + _PARAMS + '\\)?' + _RETURN_TYPE + '?\\s*=>'
    },
    CodeElementType.IMPORT: {
        'tree_sitter_query': _TS_IMPORT_QUERY, # Uses simple query, logic issue likely elsewhere
        'custom_extract': True,
        'IMPORT_NODE': 'import_statement',
        'IMPORT_PATTERN': '(?:^|\\n)\\s*(?:import(?:\\s+(?:[\\w*{},\\s]+)\\s+from)?\\s+[\'"].*?[\'"];?|export\\s+(?:\\*|{[^}]+})\\s+from\\s+[\'"].*?[\'"];?)'
    },
    CodeElementType.PROPERTY: {
        'tree_sitter_query': _TS_PROPERTY_QUERY, # Uses REVISED query
        'PROPERTY_NODE': 'public_field_definition', 'NAME_NODE': 'property_identifier', 'TYPE_NODE': 'type_annotation', 'VALUE_NODE': '_',
        'PROPERTY_PATTERN': '(?:^|\\n)\\s*' + _OPTIONAL_ACCESS + '(?:readonly\\s+)?' + _IDENTIFIER + _TYPE_ANNOTATION + '?\\s*(?:=\\s*[^;\\n]+?)?\\s*;?',
        'IDENTIFIER_PATTERN': _IDENTIFIER
    },
    CodeElementType.STATIC_PROPERTY: {
        'tree_sitter_query': _TS_PROPERTY_QUERY, # Uses REVISED query (same as PROPERTY)
        'STATIC_PROP_NODE': 'public_field_definition', 'NAME_NODE': 'property_identifier',
        'IDENTIFIER_PATTERN': _IDENTIFIER, 'OPTIONAL_NEWLINE_INDENT': '(?:^|\\n)\\s+',
        'OPTIONAL_TYPE_HINT': _TYPE_ANNOTATION + '?', 'VALUE_CAPTURE': _VALUE_CAPTURE,
        'OPTIONAL_COMMENT_ENDLINE': _OPTIONAL_COMMENT_ENDLINE
    },
    CodeElementType.PROPERTY_GETTER: {
        'tree_sitter_query': _TS_METHOD_QUERY, # Uses REVISED METHOD query
        'NAME_NODE': 'property_identifier', 'GETTER_DECORATOR_ID': 'get',
        'GETTER_DECORATOR_PATTERN': _OPTIONAL_ACCESS + 'get', 'METHOD_PATTERN': 'get\\s+' + _IDENTIFIER,
        'IDENTIFIER_PATTERN': _IDENTIFIER, 'FIRST_PARAM_PATTERN': '', 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?',
        'BODY_CAPTURE_LOOKAHEAD': _BODY_START + '[\\s\\S]*'
    },
    CodeElementType.PROPERTY_SETTER: {
        'tree_sitter_query': _TS_METHOD_QUERY, # Uses REVISED METHOD query
        'NAME_NODE': 'property_identifier', 'SETTER_DECORATOR_ATTR': 'set',
        'PROPERTY_NAME_PATTERN': _IDENTIFIER, 'SETTER_ATTR_PATTERN': 'set',
        'METHOD_PATTERN': 'set\\s+' + _IDENTIFIER, 'IDENTIFIER_PATTERN': _IDENTIFIER,
        'FIRST_PARAM_PATTERN': _IDENTIFIER, 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?',
        'BODY_CAPTURE_LOOKAHEAD': _BODY_START + '[\\s\\S]*'
    },
    CodeElementType.DECORATOR: {
        'tree_sitter_query': _TS_DECORATOR_QUERY, # Uses REVISED query
        'DECORATOR_NODE': 'decorator', 'DECORATOR_PREFIX': '@',
        'QUALIFIED_NAME_PATTERN': _IDENTIFIER + '(?:\\.' + _IDENTIFIER + ')*',
        'ARGS_PATTERN': '(?:\\([^)]*\\))?'
    },
    CodeElementType.TYPE_ALIAS: {
        'tree_sitter_query': _TS_TYPE_ALIAS_QUERY,
        'TYPE_NODE': 'type_alias_declaration', 'NAME_NODE': 'type_identifier', 'VALUE_NODE': '_',
        'TYPE_PATTERN': '(?:export\\s+)?type', 'IDENTIFIER_PATTERN': _IDENTIFIER
    },
    CodeElementType.ENUM: {
        'tree_sitter_query': _TS_ENUM_QUERY,
        'ENUM_NODE': 'enum_declaration', 'NAME_NODE': 'identifier', 'BODY_NODE': 'enum_body',
        'ENUM_PATTERN': '(?:export\\s+)?enum'
    },
    CodeElementType.NAMESPACE: {
        'tree_sitter_query': _TS_NAMESPACE_QUERY,
        'NAMESPACE_NODE': 'module', 'NAME_NODE': 'identifier', 'BODY_NODE': 'module_body',
        'NAMESPACE_PATTERN': '(?:export\\s+)?(?:namespace|module)'
    }
}

# --- Main Language Configuration Dictionary ---
LANGUAGE_CONFIG = {
    'language_code': 'typescript',
    'formatter_class': TypeScriptFormatter,
    'post_processor_class': TypeScriptExtractionPostProcessor,
    'template_placeholders': TS_PLACEHOLDERS
}