# d:\code\codehem\codehem\languages\lang_typescript\config.py
# Revised version based on test_ts2.py analysis

"""
Language-specific configuration for TypeScript/JavaScript in CodeHem.
(Combined Corrected Queries, Capture Names, and Placeholders)
"""
import json
from pathlib import Path
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
  name: (property_identifier) @method_name
  parameters: (formal_parameters) @params
  return_type: (type_annotation)? @return_type
  body: (statement_block)? @body
) @method_def
"""

# Properties (Class Fields / Interface Signatures) - REVISED
_TS_PROPERTY_QUERY = """
(public_field_definition
  name: (property_identifier) @property_name
  type: (type_annotation)? @type
  value: (_)? @value
) @property_def
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
_IDENTIFIER = "[a-zA-Z_$][a-zA-Z0-9_$]*"
_PARAMS = "[^)]*"
_TYPE_ANNOTATION = "(?:\\s*:\\s*[\\w.<>\\[\\]|&\\s'\"{}()=>]+)?"
_RETURN_TYPE = "(?:\\s*:\\s*[\\w.<>\\[\\]|&\\s'\"{}()=>]+)"
_OPTIONAL_ASYNC = "(?:async\\s+)?"
_OPTIONAL_ACCESS = "(?:(?:public|private|protected|static|readonly)\\s+)*"
_BODY_START = "{"
_DECORATOR_REGEX = "@" + _IDENTIFIER + "(?:\\([^)]*\\))?"
_INHERITANCE = "(?:\\s+(?:extends|implements)\\s+[\\w.,\\s<>]+)?"
_FIRST_PARAM = "(?:this|" + _IDENTIFIER + ")"
_VALUE_CAPTURE = ".+?"
_OPTIONAL_COMMENT_ENDLINE = "(?:$|\\s*//|\\s*/\\*)"

# --- Mapping Element Types to Queries and Placeholders ---
_patterns_path = Path(__file__).with_name("node_patterns.json")
with _patterns_path.open() as f:
    _raw_patterns = json.load(f)
TS_PLACEHOLDERS = {CodeElementType(k): v for k, v in _raw_patterns.items()}


# --- Main Language Configuration Dictionary ---
LANGUAGE_CONFIG = {
    "language_code": "typescript",
    "formatter_class": TypeScriptFormatter,
    "post_processor_class": TypeScriptExtractionPostProcessor,
    "template_placeholders": TS_PLACEHOLDERS,
}
