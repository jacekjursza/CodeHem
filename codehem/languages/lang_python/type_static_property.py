# codehem/languages/lang_python/type_static_property.py

from codehem.core.registry import element_type_descriptor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType

@element_type_descriptor
class PythonStaticPropertyHandlerElementType(ElementTypeLanguageDescriptor):
    """Handler for Python static property elements."""
    language_code = 'python'
    element_type = CodeElementType.STATIC_PROPERTY

    # --- Simplified Tree-sitter Query ---
    # Focuses only on simple assignments (identifier = value) to avoid syntax errors.
    # This might miss type-hinted assignments via TreeSitter, relying on Regex fallback.
    # Further refinement based on actual AST for typed assignments is needed for full TS support.
    tree_sitter_query = """
    (class_definition
      body: (block .           ; Match within the class body block
        (expression_statement  ; Within an expression statement
          (assignment          ; Match an assignment node
            left: (identifier) @prop_name   ; Left side MUST be a simple identifier
            right: (_) @prop_value          ; Capture the right side (value)
          )
        ) @static_prop_def       ; Capture the whole statement
      )
    )
    """
    # --- Updated Regex Pattern (from previous correction) ---
    # Added optional non-capturing group for ': type'
    # Made the value part slightly more robust (allows more characters, non-greedy)
    regexp_pattern = r'(?:^|\n)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*(?::\s*[^=]+?)?\s*=\s*(.+?)(?:\s*#.*)?(?:\n|$)'
    custom_extract = False