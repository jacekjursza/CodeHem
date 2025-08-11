# Content of codehem\models\element_type_template.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Mapping
import logging
import sys
import re
# Removed rich import - not essential here
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

@dataclass
class ElementTypeTemplate:
    """
    Template defining the base structure and patterns (with placeholders)
    for different code element types.
    """
    element_type: CodeElementType
    description: str
    tree_sitter_pattern: Optional[str] = None # Default TS pattern with placeholders
    regexp_pattern: Optional[str] = None    # Default Regex pattern with placeholders
    custom_extract: bool = False

    def format_patterns(self, language_placeholders: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Generate descriptor attributes by formatting this template's patterns
        using the provided full language placeholder map.
        Returns a dictionary with formatted patterns or None if formatting fails.
        """
        # This method now expects the specific placeholders map for the element type
        # e.g. language_placeholders[CodeElementType.CLASS]
        specific_placeholders = language_placeholders # Rename for clarity within this method

        if not isinstance(specific_placeholders, Mapping):
            logger.error(f"Invalid specific_placeholders provided to format_patterns for template '{self.element_type.value}': Expected a dictionary/mapping, got {type(specific_placeholders)}.")
            return None

        tree_sitter_query_template = self.tree_sitter_pattern
        regexp_pattern_template = self.regexp_pattern
        formatted_ts_query = None
        formatted_regexp = None

        # Format TreeSitter pattern if template exists
        if tree_sitter_query_template:
            try:
                ts_keys_needed = set(re.findall('\\{([^{}]+)\\}', tree_sitter_query_template))
                if not ts_keys_needed:
                    formatted_ts_query = tree_sitter_query_template # No placeholders needed
                else:
                    missing_keys = ts_keys_needed - set(specific_placeholders.keys())
                    if missing_keys:
                        # Lower severity: missing placeholders is expected when a language supplies direct queries
                        logger.debug(f'Formatting TreeSitter pattern for {self.element_type.value}: Missing placeholders {missing_keys}; will fall back to direct definitions if provided. Template: {repr(tree_sitter_query_template)}')
                        formatted_ts_query = None # Indicate failure
                    else:
                        formatting_dict = {k: specific_placeholders[k] for k in ts_keys_needed}
                        formatted_ts_query = tree_sitter_query_template.format(**formatting_dict)
            except KeyError as e:
                logger.error(f'Formatting TreeSitter pattern for {self.element_type.value}: KeyError - Missing key {e}. Specific Placeholders: {list(specific_placeholders.keys())}', exc_info=True)
                formatted_ts_query = None
            except Exception as e:
                logger.error(f'Formatting TreeSitter pattern for {self.element_type.value}: Unexpected error {e}', exc_info=True)
                formatted_ts_query = None
        # else: No TS template pattern defined in BASE_TEMPLATES

        # Format Regex pattern if template exists
        if regexp_pattern_template:
            try:
                rx_keys_needed = set(re.findall('\\{([^{}]+)\\}', regexp_pattern_template))
                if not rx_keys_needed:
                    formatted_regexp = regexp_pattern_template
                else:
                    missing_keys = rx_keys_needed - set(specific_placeholders.keys())
                    if missing_keys:
                        logger.debug(f'Formatting Regex pattern for {self.element_type.value}: Missing placeholders {missing_keys}; will fall back to direct definitions if provided. Template: {repr(regexp_pattern_template)}')
                        formatted_regexp = None
                    else:
                        formatting_dict = {k: specific_placeholders[k] for k in rx_keys_needed}
                        formatted_regexp = regexp_pattern_template.format(**formatting_dict)
            except KeyError as e:
                logger.error(f'Formatting Regex pattern for {self.element_type.value}: KeyError - Missing key {e}. Specific Placeholders: {list(specific_placeholders.keys())}', exc_info=True)
                formatted_regexp = None
            except Exception as e:
                logger.error(f'Formatting Regex pattern for {self.element_type.value}: Unexpected error {e}', exc_info=True)
                formatted_regexp = None
        # else: No Regex template pattern defined in BASE_TEMPLATES

        # Determine final custom_extract flag (prefer value from placeholders if present)
        custom_extract_final = specific_placeholders.get('custom_extract', self.custom_extract)
        if not isinstance(custom_extract_final, bool):
             custom_extract_final = self.custom_extract

        # Check if formatting succeeded for patterns that had a template
        # A pattern is considered "OK" if either its template didn't exist, or if formatting succeeded
        ts_ok = not tree_sitter_query_template or formatted_ts_query is not None
        rx_ok = not regexp_pattern_template or formatted_regexp is not None

        if ts_ok and rx_ok:
            # Return the potentially formatted patterns
            return {
                'tree_sitter_query': formatted_ts_query, # Could be None if template was None
                'regexp_pattern': formatted_regexp,     # Could be None if template was None
                'custom_extract': custom_extract_final
            }
        else:
            # Lower severity: template formatting may legitimately fail when language supplies direct patterns
            logger.debug(f'Pattern formatting not applied for {self.element_type.value}. TS OK: {ts_ok}, RX OK: {rx_ok}')
            return None # Explicitly return None if formatting failed

# --- Base Templates (Restore tree_sitter_pattern defaults with placeholders) ---
CLASS_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.CLASS, description='Class definition element', tree_sitter_pattern='({CLASS_NODE} name: ({NAME_NODE}) @class_name body: ({BODY_NODE}) @body) @class_def', regexp_pattern='{CLASS_PATTERN}\\s+({IDENTIFIER_PATTERN})(?:{INHERITANCE_PATTERN})?\\s*{BODY_START}')
METHOD_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.METHOD, description='Method definition element', tree_sitter_pattern='(function_definition name: ({NAME_NODE}) @method_name) @method_def', regexp_pattern='(?:^|\\n)\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_ID}[^)]*\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}')
FUNCTION_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.FUNCTION, description='Standalone function definition element', tree_sitter_pattern='(function_definition name: ({NAME_NODE}) @function_name) @function_def', regexp_pattern='(?:^|\\n)\\s*(?:async\\s+)?{FUNCTION_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\({PARAMS_PATTERN}\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}')
IMPORT_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.IMPORT, description='Import statement element', tree_sitter_pattern='(import_statement) @import_statement', regexp_pattern='{IMPORT_PATTERN}', custom_extract=True)
PROPERTY_GETTER_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.PROPERTY_GETTER, description='Property getter method', tree_sitter_pattern='(method_definition kind:(get) name:({NAME_NODE}) @getter_name) @getter_def', regexp_pattern='{GETTER_DECORATOR_PATTERN}\\s*\\n\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*:{BODY_CAPTURE_LOOKAHEAD}')
PROPERTY_SETTER_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.PROPERTY_SETTER, description='Property setter method', tree_sitter_pattern='(method_definition kind:(set) name:({NAME_NODE}) @setter_name) @setter_def', regexp_pattern='@{PROPERTY_NAME_PATTERN}\\.{SETTER_ATTR_PATTERN}\\s*\\n\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*:{BODY_CAPTURE_LOOKAHEAD}')
STATIC_PROPERTY_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.STATIC_PROPERTY, description='Static class property', tree_sitter_pattern='(field_definition (static) name:({NAME_NODE})) @static_prop_def', regexp_pattern='{OPTIONAL_NEWLINE_INDENT}({IDENTIFIER_PATTERN}){OPTIONAL_TYPE_HINT}\\s*=\\s*({VALUE_CAPTURE}){OPTIONAL_COMMENT_ENDLINE}')
DECORATOR_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.DECORATOR, description='Decorator element', tree_sitter_pattern='(decorator) @decorator_node', regexp_pattern='{DECORATOR_PREFIX}({QUALIFIED_NAME_PATTERN})(?:{ARGS_PATTERN})?')
INTERFACE_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.INTERFACE, description='Interface definition element', tree_sitter_pattern='({INTERFACE_NODE} name: ({NAME_NODE}) @interface_name body: ({BODY_NODE}) @body) @interface_def', regexp_pattern='{INTERFACE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)(?:{EXTENDS_PATTERN})?\\s*{BODY_START}')
TYPE_ALIAS_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.TYPE_ALIAS, description='Type alias definition element', tree_sitter_pattern='({TYPE_NODE} name: ({NAME_NODE}) @type_name) @type_def', regexp_pattern='{TYPE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\\s*=')
ENUM_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.ENUM, description='Enum definition element', tree_sitter_pattern='({ENUM_NODE} name: ({NAME_NODE}) @enum_name body: ({BODY_NODE}) @body) @enum_def', regexp_pattern='{ENUM_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)')
NAMESPACE_TEMPLATE = ElementTypeTemplate(element_type=CodeElementType.NAMESPACE, description='Namespace/Module definition element', tree_sitter_pattern='({NAMESPACE_NODE} name: ({NAME_NODE}) @namespace_name body: ({BODY_NODE}) @body) @namespace_def', regexp_pattern='{NAMESPACE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)')

BASE_TEMPLATES: Dict[CodeElementType, ElementTypeTemplate] = {
    CodeElementType.CLASS: CLASS_TEMPLATE,
    CodeElementType.METHOD: METHOD_TEMPLATE,
    CodeElementType.FUNCTION: FUNCTION_TEMPLATE,
    CodeElementType.IMPORT: IMPORT_TEMPLATE,
    CodeElementType.INTERFACE: INTERFACE_TEMPLATE,
    CodeElementType.TYPE_ALIAS: TYPE_ALIAS_TEMPLATE,
    CodeElementType.PROPERTY_GETTER: PROPERTY_GETTER_TEMPLATE,
    CodeElementType.PROPERTY_SETTER: PROPERTY_SETTER_TEMPLATE,
    CodeElementType.STATIC_PROPERTY: STATIC_PROPERTY_TEMPLATE,
    CodeElementType.DECORATOR: DECORATOR_TEMPLATE,
    CodeElementType.ENUM: ENUM_TEMPLATE,
    CodeElementType.NAMESPACE: NAMESPACE_TEMPLATE
}

# --- Modified create_element_type_descriptor ---
def create_element_type_descriptor(
    language_code: str,
    element_type: CodeElementType,
    # Expects the entire placeholder map for the language, e.g., lang_config['template_placeholders']
    language_placeholders: Mapping[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Factory method to create descriptor attributes.
    It attempts to format the base template's patterns using the language-specific placeholders.
    If formatting fails or a base pattern doesn't exist, it checks if the patterns
    are defined directly within the language placeholders.
    """
    base_template = BASE_TEMPLATES.get(element_type)
    specific_placeholders = language_placeholders.get(element_type, {})

    if not isinstance(specific_placeholders, Mapping):
        logger.error(f"Invalid placeholder structure for element type '{element_type.value}' in language '{language_code}': Expected dict, got {type(specific_placeholders)}.")
        return None

    # --- Corrected Logic Start ---
    formatted_attrs_from_template: Optional[Dict[str, Any]] = None
    if base_template:
        # Attempt to format using the base template and specific placeholders
        formatted_attrs_from_template = base_template.format_patterns(specific_placeholders)
        # format_patterns returns None on failure

    # Initialize final attributes, prioritizing direct definitions in placeholders
    final_attrs = {}

    # Tree-sitter query: Use direct definition if available, otherwise use formatted template result (if successful)
    if 'tree_sitter_query' in specific_placeholders:
        final_attrs['tree_sitter_query'] = specific_placeholders['tree_sitter_query']
        logger.debug(f"Using 'tree_sitter_query' directly from placeholders for {language_code}/{element_type.value}")
    elif formatted_attrs_from_template and formatted_attrs_from_template.get('tree_sitter_query') is not None:
        final_attrs['tree_sitter_query'] = formatted_attrs_from_template['tree_sitter_query']
        logger.debug(f"Using 'tree_sitter_query' formatted from base template for {language_code}/{element_type.value}")
    else:
        # Neither direct definition nor successful formatting from template
        if base_template and base_template.tree_sitter_pattern: # Warn only if template existed but formatting failed
             logger.warning(f"Failed to format or find direct 'tree_sitter_query' for {language_code}/{element_type.value}.")
        else: # No template pattern defined
             logger.debug(f"No 'tree_sitter_query' defined in placeholders or base template for {language_code}/{element_type.value}.")
        final_attrs['tree_sitter_query'] = None

    # Regex pattern: Use direct definition if available, otherwise use formatted template result (if successful)
    if 'regexp_pattern' in specific_placeholders:
        final_attrs['regexp_pattern'] = specific_placeholders['regexp_pattern']
        logger.debug(f"Using 'regexp_pattern' directly from placeholders for {language_code}/{element_type.value}")
    elif formatted_attrs_from_template and formatted_attrs_from_template.get('regexp_pattern') is not None:
        final_attrs['regexp_pattern'] = formatted_attrs_from_template['regexp_pattern']
        logger.debug(f"Using 'regexp_pattern' formatted from base template for {language_code}/{element_type.value}")
    else:
        # If we already have a valid tree-sitter query, lack of regex is not an issue.
        has_ts = final_attrs.get('tree_sitter_query') is not None
        if base_template and base_template.regexp_pattern:
            (logger.debug if has_ts else logger.warning)(
                f"Failed to format or find direct 'regexp_pattern' for {language_code}/{element_type.value}."
            )
        else:
            logger.debug(
                f"No 'regexp_pattern' defined in placeholders or base template for {language_code}/{element_type.value}."
            )
        final_attrs['regexp_pattern'] = None

    # Handle custom_extract flag (Placeholder definition takes precedence over template)
    custom_extract_final = specific_placeholders.get('custom_extract', getattr(base_template, 'custom_extract', False))
    if not isinstance(custom_extract_final, bool):
         custom_extract_final = False
    final_attrs['custom_extract'] = custom_extract_final

    # Add language_code and element_type
    final_attrs['language_code'] = language_code
    final_attrs['element_type'] = element_type

    # Log final state
    ts_status = 'Yes' if final_attrs.get('tree_sitter_query') else 'No'
    rx_status = 'Yes' if final_attrs.get('regexp_pattern') else 'No'
    logger.debug(f"Final attributes for {language_code}/{element_type.value}: TS={ts_status}, RX={rx_status}, Custom={custom_extract_final}")

    # Return the final dictionary (guaranteed to be a dict, patterns can be None)
    return final_attrs
    # --- Corrected Logic End ---
