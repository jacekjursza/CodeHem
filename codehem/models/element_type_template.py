# MODIFIED FILE: Removed exclusion for dunder methods in METHOD_TEMPLATE query
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Mapping
import logging
import sys
import re
from codehem.models.enums import CodeElementType
from codehem.core.registry import registry

logger = logging.getLogger(__name__)

@dataclass
class ElementTypeTemplate:
    """Template for creating language-specific element type descriptors."""
    element_type: CodeElementType
    description: str
    tree_sitter_pattern: Optional[str] = None
    regexp_pattern: Optional[str] = None
    custom_extract: bool = False # Flag if descriptor handles extraction itself

    def format_patterns(self, placeholders: Mapping[str, str]) -> Optional[Dict[str, Any]]:
        """
        Generate descriptor attributes by formatting patterns with provided placeholders.
        Returns a dictionary with formatted patterns or None if formatting fails.
        """
        if not isinstance(placeholders, Mapping):
            logger.error(f"Invalid placeholders provided for template '{self.element_type.value}': Expected a dictionary, got {type(placeholders)}.")
            return None

        tree_sitter_query = self.tree_sitter_pattern
        regexp = self.regexp_pattern
        formatted_ts_query = tree_sitter_query
        formatted_regexp = regexp

        if tree_sitter_query:
            try:
                ts_keys_needed = set(re.findall(r'\{([^{}]+)\}', tree_sitter_query))
                if ts_keys_needed:
                    missing_keys = ts_keys_needed - set(placeholders.keys())
                    if missing_keys:
                        logger.error(f'Formatting TreeSitter pattern for {self.element_type.value}: Missing placeholders {missing_keys} in provided map.')
                        formatted_ts_query = None
                    else:
                        formatting_dict = {k: placeholders[k] for k in ts_keys_needed}
                        formatted_ts_query = tree_sitter_query.format(**formatting_dict)
            except KeyError as e:
                 logger.error(f'Formatting TreeSitter pattern for {self.element_type.value}: KeyError - Missing key {e}.', exc_info=True)
                 formatted_ts_query = None
            except Exception as e:
                 logger.error(f'Formatting TreeSitter pattern for {self.element_type.value}: Unexpected error {e}', exc_info=True)
                 formatted_ts_query = None

        if regexp:
             try:
                rx_keys_needed = set(re.findall(r'\{([^{}]+)\}', regexp))
                if rx_keys_needed:
                    missing_keys = rx_keys_needed - set(placeholders.keys())
                    if missing_keys:
                         logger.error(f'Formatting Regex pattern for {self.element_type.value}: Missing placeholders {missing_keys} in provided map.')
                         formatted_regexp = None
                    else:
                         formatting_dict = {k: placeholders[k] for k in rx_keys_needed}
                         formatted_regexp = regexp.format(**formatting_dict)
             except KeyError as e:
                 logger.error(f'Formatting Regex pattern for {self.element_type.value}: KeyError - Missing key {e}.', exc_info=True)
                 formatted_regexp = None
             except Exception as e:
                 logger.error(f'Formatting Regex pattern for {self.element_type.value}: Unexpected error {e}', exc_info=True)
                 formatted_regexp = None

        ts_ok = (not self.tree_sitter_pattern) or (formatted_ts_query is not None)
        rx_ok = (not self.regexp_pattern) or (formatted_regexp is not None)

        if ts_ok and rx_ok:
            return {
                'tree_sitter_query': formatted_ts_query,
                'regexp_pattern': formatted_regexp,
                'custom_extract': self.custom_extract
            }
        else:
            logger.error(f'Not all required patterns could be generated for {self.element_type.value}. TS OK: {ts_ok}, RX OK: {rx_ok}')
            return None

# Define BASE templates as constants within this module
CLASS_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.CLASS,
    description='Class definition element',
    tree_sitter_pattern='({CLASS_NODE} name: ({NAME_NODE}) @class_name body: ({BODY_NODE}) @body) @class_def',
    regexp_pattern='{CLASS_PATTERN}\\s+({IDENTIFIER_PATTERN})(?:{INHERITANCE_PATTERN})?\\s*{BODY_START}'
)

# *** CHANGE START: Removed #match? exclusion from METHOD_TEMPLATE query ***
METHOD_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.METHOD,
    description='Method definition element (member function)',
    tree_sitter_pattern='''
    (function_definition
        name: ({NAME_NODE}) @method_name
        ; Removed exclusion: (#match? @method_name "^(?!__).*")
    ) @method_def

    (decorated_definition
     definition: (function_definition
                    name: ({NAME_NODE}) @method_name
                    ; Removed exclusion: (#match? @method_name "^(?!__).*")
                )
    ) @decorated_method_def
    ''',
    regexp_pattern='(?:^|\\n)\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_ID}[^)]*\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}'
)
# *** CHANGE END ***

FUNCTION_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.FUNCTION,
    description='Standalone function definition element (sync or async)',
    tree_sitter_pattern='''
    (function_definition
        name: ({NAME_NODE}) @function_name
    ) @function_def

    (decorated_definition
        definition: (function_definition
            name: ({NAME_NODE}) @function_name
        )
    ) @decorated_function_def
    ''',
    regexp_pattern='(?:^|\\n)\\s*(?:async\\s+)?{FUNCTION_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\({PARAMS_PATTERN}\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}'
)

IMPORT_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.IMPORT,
    description='Import statement element',
    tree_sitter_pattern='(import_statement) @import_simple (import_from_statement) @import_from',
    regexp_pattern='{IMPORT_PATTERN}',
    custom_extract=False
)

PROPERTY_GETTER_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.PROPERTY_GETTER,
    description='Property getter method',
    tree_sitter_pattern='''
    (decorated_definition
        (decorator (identifier) @decorator_name)
        definition: (function_definition name: ({NAME_NODE}) @property_name)
        (#eq? @decorator_name "{GETTER_DECORATOR_ID}")
    ) @property_def
    ''',
    regexp_pattern='{GETTER_DECORATOR_PATTERN}\\s*\\n\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*:{BODY_CAPTURE_LOOKAHEAD}'
)

PROPERTY_SETTER_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.PROPERTY_SETTER,
    description='Property setter method',
    tree_sitter_pattern='''
    (decorated_definition
        (decorator (attribute object: (identifier) @prop_obj attribute: (identifier) @decorator_attr))
        definition: (function_definition name: ({NAME_NODE}) @property_name)
        (#eq? @decorator_attr "{SETTER_DECORATOR_ATTR}")
        (#eq? @prop_obj @property_name) ; Ensure decorator object matches method name
    ) @property_setter_def
    ''',
    regexp_pattern='@{PROPERTY_NAME_PATTERN}\\.{SETTER_ATTR_PATTERN}\\s*\\n\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*:{BODY_CAPTURE_LOOKAHEAD}'
)

STATIC_PROPERTY_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.STATIC_PROPERTY,
    description='Static class property (class variable)',
    tree_sitter_pattern='(class_definition body: (block) @class_block)',
    regexp_pattern='{OPTIONAL_NEWLINE_INDENT}({IDENTIFIER_PATTERN}){OPTIONAL_TYPE_HINT}\\s*=\\s*({VALUE_CAPTURE}){OPTIONAL_COMMENT_ENDLINE}'
)

DECORATOR_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.DECORATOR,
    description='Decorator element',
    tree_sitter_pattern='(decorator) @decorator_node',
    regexp_pattern='{DECORATOR_PREFIX}({QUALIFIED_NAME_PATTERN})(?:{ARGS_PATTERN})?'
)

INTERFACE_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.INTERFACE,
    description='Interface definition element',
    tree_sitter_pattern='({INTERFACE_NODE} name: ({NAME_NODE}) @interface_name body: ({BODY_NODE}) @body) @interface_def',
    regexp_pattern='{INTERFACE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)(?:{EXTENDS_PATTERN})?\\s*{BODY_START}'
)

TYPE_ALIAS_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.TYPE_ALIAS,
    description='Type alias definition element',
    tree_sitter_pattern='({TYPE_NODE} name: ({NAME_NODE}) @type_name) @type_def',
    regexp_pattern='{TYPE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\\s*='
)

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
}

def create_element_type_descriptor(language_code: str, element_type: CodeElementType) -> Optional[Dict[str, Any]]:
    """
    Factory method to create element type descriptor attributes for a language.
    Fetches language config and base template, then formats patterns.
    """
    base_template = BASE_TEMPLATES.get(element_type)
    if not base_template:
        logger.debug(f'No base template found for element type: {element_type.value}')
        return None

    lang_config = registry.get_language_config(language_code)
    if not lang_config:
         # Log error here instead of inside the loop in LanguageService.__init__
         logger.error(f"Could not retrieve language configuration for '{language_code}' from registry.")
         return None # Cannot proceed without config

    all_language_placeholders = lang_config.get('template_placeholders', {})
    if not isinstance(all_language_placeholders, Mapping):
         logger.error(f"Invalid 'template_placeholders' format in config for '{language_code}': Expected dict, got {type(all_language_placeholders)}.")
         return None # Cannot proceed without valid placeholders map

    specific_placeholders = all_language_placeholders.get(element_type, {})
    if not isinstance(specific_placeholders, Mapping):
         logger.error(f"Invalid placeholder format for element type '{element_type.value}' in config for '{language_code}': Expected dict, got {type(specific_placeholders)}.")
         specific_placeholders = {}

    formatted_attributes = base_template.format_patterns(specific_placeholders)

    if formatted_attributes is None:
        logger.warning(f"Pattern generation failed for {language_code}/{element_type.value}.")
        return None

    formatted_attributes['language_code'] = language_code
    formatted_attributes['element_type'] = element_type

    return formatted_attributes