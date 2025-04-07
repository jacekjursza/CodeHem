# Content of codehem\languages\lang_typescript\config.py
"""
Language-specific configuration for TypeScript/JavaScript in CodeHem.
(Combined Corrected Queries, Capture Names, and Placeholders)
"""
from codehem.models.enums import CodeElementType
from .typescript_post_processor import TypeScriptExtractionPostProcessor
from .formatting.typescript_formatter import TypeScriptFormatter

# --- Corrected Tree-sitter Queries with Aligned Capture Names ---

_TS_IMPORT_QUERY = """
(import_statement) @import_statement
"""

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

_TS_INTERFACE_QUERY = """
(interface_declaration
  name: (type_identifier) @interface_name
  body: (interface_body) @interface_body ; Corrected body type
) @interface_def

(export_statement
  declaration: (interface_declaration
    name: (type_identifier) @interface_name
    body: (interface_body) @interface_body ; Corrected body type
  ) @interface_def_exported
)
"""

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

_TS_METHOD_QUERY = """
(method_definition
  (static)? @static_kind
  (accessibility_modifier)? @accessibility
  (readonly)? @readonly_kind
  kind: (get)? @getter_kind
  kind: (set)? @setter_kind
  name: (property_identifier) @method_name ; Generic name capture
  parameters: (formal_parameters) @params
  return_type: (type_annotation)? @return_type
  body: (statement_block)? @body
) @method_def ; Capture the whole definition
"""

_TS_PROPERTY_QUERY = """
(public_field_definition
  (accessibility_modifier)? @accessibility
  (static)? @static
  (readonly)? @readonly
  name: (property_identifier) @property_name
  type: (type_annotation)? @type
  value: (_)? @value
) @property_def

(property_signature
  (readonly)? @readonly
  name: (property_identifier) @property_name ; Use consistent name
  (question_mark)? @optional
  type: (type_annotation)? @type
) @interface_property_def
"""

_TS_DECORATOR_QUERY = """
(decorator
  expression: (_) @decorator_expression
) @decorator_node
"""

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

# --- Placeholders Definitions (Include necessary keys for BASE_TEMPLATES) ---
# Define placeholders based on actual TS node types identified via AST dump
_IDENTIFIER = '[a-zA-Z_$][a-zA-Z0-9_$]*' # Reusable regex part
_PARAMS = '[^)]*' # Reusable regex part
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

TS_PLACEHOLDERS = {
    CodeElementType.CLASS: {
        'tree_sitter_query': _TS_CLASS_QUERY,
        'CLASS_NODE': 'class_declaration', 'NAME_NODE': 'type_identifier', 'BODY_NODE': 'class_body',
        'CLASS_PATTERN': '(?:export\\s+)?(?:abstract\\s+)?class', 'IDENTIFIER_PATTERN': _IDENTIFIER, 'INHERITANCE_PATTERN': _INHERITANCE, 'BODY_START': _BODY_START
    },
    CodeElementType.INTERFACE: {
        'tree_sitter_query': _TS_INTERFACE_QUERY,
        'INTERFACE_NODE': 'interface_declaration', 'NAME_NODE': 'type_identifier', 'BODY_NODE': 'interface_body',
        'INTERFACE_PATTERN': '(?:export\\s+)?interface', 'IDENTIFIER_PATTERN': _IDENTIFIER, 'EXTENDS_PATTERN': '(?:\\s+extends\\s+[\\w.,\\s<>]+)?', 'BODY_START': _BODY_START
    },
    CodeElementType.METHOD: {
        'tree_sitter_query': _TS_METHOD_QUERY,
        'NAME_NODE': 'property_identifier', 'FIRST_PARAM_ID': 'this', # Placeholder needed by template
        'METHOD_PATTERN': _OPTIONAL_ACCESS + _OPTIONAL_ASYNC + _IDENTIFIER, 'IDENTIFIER_PATTERN': _IDENTIFIER, 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?', 'BODY_START': _BODY_START
    },
    CodeElementType.FUNCTION: {
        'tree_sitter_query': _TS_FUNCTION_QUERY,
        'NAME_NODE': 'identifier', 'PARAMS_NODE': 'formal_parameters', 'RETURN_TYPE_NODE': 'type_annotation', 'BODY_NODE': 'statement_block',
        'FUNCTION_PATTERN': '(?:export\\s+)?' + _OPTIONAL_ASYNC + 'function', 'IDENTIFIER_PATTERN': _IDENTIFIER, 'PARAMS_PATTERN': _PARAMS, 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?', 'BODY_START': _BODY_START,
        'ARROW_FUNCTION_PATTERN': '(?:export\\s+)?(?:const|let)\\s+' + _IDENTIFIER + '\\s*[:]?.*=\\s*' + _OPTIONAL_ASYNC + '\\(?' + _PARAMS + '\\)?' + _RETURN_TYPE + '?\\s*=>'
    },
    CodeElementType.IMPORT: {
        'tree_sitter_query': _TS_IMPORT_QUERY,
        'IMPORT_NODE': 'import_statement', # Placeholder for template
        'IMPORT_PATTERN': '(?:^|\\n)\\s*(?:import(?:\\s+(?:[\\w*{},\\s]+)\\s+from)?\\s+[\'"].*?[\'"];?|export\\s+(?:\\*|{[^}]+})\\s+from\\s+[\'"].*?[\'"];?)'
    },
    CodeElementType.PROPERTY: {
        'tree_sitter_query': _TS_PROPERTY_QUERY,
        'PROPERTY_NODE': 'public_field_definition', 'NAME_NODE': 'property_identifier', 'TYPE_NODE': 'type_annotation', 'VALUE_NODE': '_',
        'PROPERTY_PATTERN': '(?:^|\\n)\\s*' + _OPTIONAL_ACCESS + '(?:readonly\\s+)?' + _IDENTIFIER + _TYPE_ANNOTATION + '?\\s*(?:=\\s*[^;\\n]+?)?\\s*;?', 'IDENTIFIER_PATTERN': _IDENTIFIER
    },
    CodeElementType.STATIC_PROPERTY: {
         'tree_sitter_query': _TS_PROPERTY_QUERY, # Reuses property query, filtered by extractor
         'STATIC_PROP_NODE': 'public_field_definition', 'NAME_NODE': 'property_identifier', # Placeholders needed by template
        'IDENTIFIER_PATTERN': _IDENTIFIER, 'OPTIONAL_NEWLINE_INDENT': '(?:^|\\n)\\s+', 'OPTIONAL_TYPE_HINT': _TYPE_ANNOTATION + '?', 'VALUE_CAPTURE': _VALUE_CAPTURE, 'OPTIONAL_COMMENT_ENDLINE': _OPTIONAL_COMMENT_ENDLINE
    },
     CodeElementType.PROPERTY_GETTER: {
        'tree_sitter_query': _TS_METHOD_QUERY, # Handled by method query
        'NAME_NODE': 'property_identifier','GETTER_DECORATOR_ID': 'get', # Placeholders needed by template
        'GETTER_DECORATOR_PATTERN': _OPTIONAL_ACCESS + 'get', 'METHOD_PATTERN': 'get\\s+' + _IDENTIFIER, 'IDENTIFIER_PATTERN': _IDENTIFIER, 'FIRST_PARAM_PATTERN': '', 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?', 'BODY_CAPTURE_LOOKAHEAD': _BODY_START + '[\\s\\S]*'
    },
    CodeElementType.PROPERTY_SETTER: {
        'tree_sitter_query': _TS_METHOD_QUERY, # Handled by method query
        'NAME_NODE': 'property_identifier','SETTER_DECORATOR_ATTR': 'set', # Placeholders needed by template
        'PROPERTY_NAME_PATTERN': _IDENTIFIER, 'SETTER_ATTR_PATTERN': 'set', 'METHOD_PATTERN': 'set\\s+' + _IDENTIFIER, 'IDENTIFIER_PATTERN': _IDENTIFIER, 'FIRST_PARAM_PATTERN': _IDENTIFIER, 'RETURN_TYPE_PATTERN': _RETURN_TYPE + '?', 'BODY_CAPTURE_LOOKAHEAD': _BODY_START + '[\\s\\S]*'
    },
    CodeElementType.DECORATOR: {
        'tree_sitter_query': _TS_DECORATOR_QUERY,
        'DECORATOR_NODE': 'decorator', # Placeholder needed by template
        'DECORATOR_PREFIX': '@', 'QUALIFIED_NAME_PATTERN': _IDENTIFIER + '(?:\\.' + _IDENTIFIER + ')*', 'ARGS_PATTERN': '(?:\\([^)]*\\))?'
    },
    CodeElementType.TYPE_ALIAS: {
        'tree_sitter_query': _TS_TYPE_ALIAS_QUERY,
        'TYPE_NODE': 'type_alias_declaration', 'NAME_NODE': 'type_identifier', 'VALUE_NODE': '_', # Placeholder needed by template
        'TYPE_PATTERN': '(?:export\\s+)?type', 'IDENTIFIER_PATTERN': _IDENTIFIER
    },
    CodeElementType.ENUM: {
        'tree_sitter_query': _TS_ENUM_QUERY,
        'ENUM_NODE': 'enum_declaration', 'NAME_NODE': 'identifier', 'BODY_NODE': 'enum_body', # Placeholders needed by template
        'ENUM_PATTERN': '(?:export\\s+)?enum'
    },
    CodeElementType.NAMESPACE: {
        'tree_sitter_query': _TS_NAMESPACE_QUERY,
        'NAMESPACE_NODE': 'module', 'NAME_NODE': 'identifier', 'BODY_NODE': 'module_body', # Placeholders needed by template
        'NAMESPACE_PATTERN': '(?:export\\s+)?(?:namespace|module)'
    }
}

# --- Final Language Configuration Dictionary ---
LANGUAGE_CONFIG = {
    'language_code': 'typescript',
    'formatter_class': TypeScriptFormatter,
    'post_processor_class': TypeScriptExtractionPostProcessor,
    'template_placeholders': TS_PLACEHOLDERS # Use the dictionary containing updated queries AND placeholders
}