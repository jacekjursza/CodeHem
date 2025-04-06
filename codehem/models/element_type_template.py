"""
Element type template system for standardizing language descriptors.
Provides templates for common code elements to generate tree-sitter queries
and regex patterns for different languages, reducing redundancy in
language-specific descriptor definitions.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import logging
import sys
import re # Added import re here as it's used below
from codehem.models.enums import CodeElementType
logger = logging.getLogger(__name__)

@dataclass
class ElementTypeTemplate:
    """Template for creating language-specific element type descriptors."""
    element_type: CodeElementType
    description: str
    tree_sitter_pattern: Optional[str] = None
    regexp_pattern: Optional[str] = None
    placeholder_map: Dict[str, Dict[str, str]] = field(default_factory=dict)
    custom_extract: bool = False

    def for_language(self, language_code: str) -> Optional[Dict[str, Any]]:
        """
        Generate descriptor attributes for a specific language.
        Returns None if the language is not configured in the placeholder_map
        and the patterns contain placeholders, or if pattern formatting fails.
        """
        placeholders = self.placeholder_map.get(language_code, {})
        tree_sitter_query = self.tree_sitter_pattern
        regexp = self.regexp_pattern

        # Check if patterns exist and contain placeholders
        has_ts_placeholders = tree_sitter_query and '{' in tree_sitter_query
        has_rx_placeholders = regexp and '{' in regexp

        # If placeholders are needed but not defined for the language, fail early
        if (has_ts_placeholders or has_rx_placeholders) and not placeholders:
            logger.error(f"Template '{self.element_type.value}' uses placeholders, but none defined for language '{language_code}'. Cannot generate attributes.")
            return None

        # Format TreeSitter query
        formatted_ts_query = tree_sitter_query
        if has_ts_placeholders:
            try:
                # Check for missing keys before formatting
                placeholders_in_pattern = set(re.findall(r'\{([^{}]+)\}', tree_sitter_query))
                missing_keys = placeholders_in_pattern - set(placeholders.keys())
                if missing_keys:
                    logger.error(f'Formatting TreeSitter pattern for {language_code}/{self.element_type.value}: Missing placeholders {missing_keys} in map.')
                    formatted_ts_query = None
                else:
                    formatted_ts_query = tree_sitter_query.format(**placeholders)
            except KeyError as e:
                logger.error(f'Formatting TreeSitter pattern for {language_code}/{self.element_type.value}: KeyError - Missing key {e} in placeholders.')
                formatted_ts_query = None
            except Exception as e:
                logger.error(f'Formatting TreeSitter pattern for {language_code}/{self.element_type.value}: Unexpected error {e}', exc_info=True)
                formatted_ts_query = None

        # Format Regex pattern
        formatted_regexp = regexp
        if has_rx_placeholders:
            try:
                # Check for missing keys before formatting
                placeholders_in_pattern = set(re.findall(r'\{([^{}]+)\}', regexp))
                missing_keys = placeholders_in_pattern - set(placeholders.keys())
                if missing_keys:
                    logger.error(f'Formatting Regex pattern for {language_code}/{self.element_type.value}: Missing placeholders {missing_keys} in map.')
                    formatted_regexp = None
                else:
                    formatted_regexp = regexp.format(**placeholders)
            except KeyError as e:
                logger.error(f'Formatting Regex pattern for {language_code}/{self.element_type.value}: KeyError - Missing key {e} in placeholders.')
                formatted_regexp = None
            except Exception as e:
                logger.error(f'Formatting Regex pattern for {language_code}/{self.element_type.value}: Unexpected error {e}', exc_info=True)
                formatted_regexp = None

        # Check if required patterns could be generated
        ts_required = bool(self.tree_sitter_pattern)
        rx_required = bool(self.regexp_pattern)
        ts_ok = not ts_required or formatted_ts_query is not None
        rx_ok = not rx_required or formatted_regexp is not None

        if ts_ok and rx_ok:
            final_ts_query = formatted_ts_query
            final_regexp = formatted_regexp
            return {
                'language_code': language_code,
                'element_type': self.element_type,
                'tree_sitter_query': final_ts_query,
                'regexp_pattern': final_regexp,
                'custom_extract': self.custom_extract
            }
        else:
            logger.error(f'Not all required patterns could be generated for {language_code}/{self.element_type.value}. TS OK: {ts_ok}, RX OK: {rx_ok}')
            return None

CLASS_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.CLASS,
    description='Class definition element',
    tree_sitter_pattern='({CLASS_NODE} name: ({NAME_NODE}) @class_name body: ({BODY_NODE}) @body) @class_def',
    regexp_pattern='{CLASS_PATTERN}\\s+({IDENTIFIER_PATTERN})(?:{INHERITANCE_PATTERN})?\\s*{BODY_START}',
    placeholder_map={
        'python': {
            'CLASS_NODE': 'class_definition',
            'NAME_NODE': 'identifier',
            'BODY_NODE': 'block',
            'CLASS_PATTERN': 'class',
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
            'INHERITANCE_PATTERN': '\\s*\\([^)]*\\)',
            'BODY_START': ':'
        },
        'typescript': {
            'CLASS_NODE': 'class_declaration',
            'NAME_NODE': 'type_identifier',
            'BODY_NODE': 'class_body',
            'CLASS_PATTERN': 'class',
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
            'INHERITANCE_PATTERN': '(?:\\s+extends\\s+[a-zA-Z_][a-zA-Z0-9_]*)?(?:\\s+implements\\s+[^{]+)?',
            'BODY_START': '\\s*\\{'
        }
    }
)

METHOD_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.METHOD,
    description='Method definition element (member function)',
    tree_sitter_pattern='''
    (function_definition
     name: ({NAME_NODE}) @method_name) @method_def

    (decorated_definition
     definition: (function_definition
                   name: ({NAME_NODE}) @method_name)) @decorated_method_def
    ''',
    regexp_pattern='(?:^|\\n)\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_ID}[^)]*\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}',
    placeholder_map={
        'python': {
            'NAME_NODE': 'identifier',
            'FIRST_PARAM_ID': 'self',
            'METHOD_PATTERN': 'def',
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
            'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
            'BODY_START': ':'
        },
        'typescript': {
            'NAME_NODE': 'property_identifier',
            'FIRST_PARAM_ID': 'this', # Simplified, might need adjustment for different contexts
            'METHOD_PATTERN': '', # Methods in TS often don't start with a keyword like 'def'
            'IDENTIFIER_PATTERN': '[a-zA-Z_$][a-zA-Z0-9_$]*', # Adjusted for TS identifiers
            'RETURN_TYPE_PATTERN': '(?:\\s*:[^{;]+)?',
            'BODY_START': '\\s*[({]' # Can start with { or ( for arrow functions
        }
    }
)

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
    regexp_pattern='(?:^|\\n)\\s*(?:async\\s+)?{FUNCTION_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\({PARAMS_PATTERN}\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}',
     placeholder_map={
        'python': {
            'NAME_NODE': 'identifier',
            'FUNCTION_PATTERN': 'def',
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
            'PARAMS_PATTERN': '(?!self\\s*[,)])[^)]*', # Avoid matching methods starting with self
            'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
            'BODY_START': ':'
        },
        'typescript': {
            'NAME_NODE': 'identifier',
            'FUNCTION_PATTERN': 'function', # Also consider arrow functions later
            'IDENTIFIER_PATTERN': '[a-zA-Z_$][a-zA-Z0-9_$]*',
            'PARAMS_PATTERN': '[^)]*',
            'RETURN_TYPE_PATTERN': '(?:\\s*:[^{;]+)?',
            'BODY_START': '\\s*\\{'
        }
    }
)

IMPORT_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.IMPORT,
    description='Import statement element',
    tree_sitter_pattern='(import_statement) @import_simple (import_from_statement) @import_from',
    regexp_pattern='{IMPORT_PATTERN}',
    custom_extract=False, # CORRECTED: Set to False to use patterns
    placeholder_map={
        'python': {'IMPORT_PATTERN': '(?:^|\\n)\\s*(import\\s+(?:[a-zA-Z0-9_.,\\s*]+)|from\\s+[a-zA-Z0-9_.]+\\s+import\\s+(?:[a-zA-Z0-9_.,\\s*()]+))'},
        'typescript': {'IMPORT_PATTERN': '(?:^|\\n)\\s*(import\\s+.*?from\\s+["\\\'][^"\\\']+["\\\'];?|import\\s*\\(.*?\\);?|require\\(.*?\\))'}
    }
)

PROPERTY_GETTER_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.PROPERTY_GETTER,
    description='Property getter method',
    tree_sitter_pattern='''
    (decorated_definition
        (decorator (identifier) @decorator_name)
        (function_definition name: ({NAME_NODE}) @property_name)
    ) @property_def
    (#eq? @decorator_name "{GETTER_DECORATOR_ID}")
    ''',
    # CORRECTED: Fixed placeholder key typo GETTER_DEcorATOR_PATTERN -> GETTER_DECORATOR_PATTERN
    regexp_pattern='{GETTER_DECORATOR_PATTERN}\\s*\\n\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*:{BODY_CAPTURE_LOOKAHEAD}',
    placeholder_map={
        'python': {
            'NAME_NODE': 'identifier',
            'GETTER_DECORATOR_ID': 'property',
            'GETTER_DECORATOR_PATTERN': '@property',
            'METHOD_PATTERN': 'def',
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
            'FIRST_PARAM_PATTERN': 'self',
            'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
            'BODY_CAPTURE_LOOKAHEAD': '(.*?)(?=\\n(?:[ \\t]*@|[ \\t]*def|\\Z))' # Lookahead to prevent grabbing next element
        }
        # Add other languages if needed
    }
)

PROPERTY_SETTER_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.PROPERTY_SETTER,
    description='Property setter method',
    tree_sitter_pattern='''
    (decorated_definition
        (decorator (attribute object: (identifier) @prop_obj attribute: (identifier) @decorator_attr))
        (function_definition name: ({NAME_NODE} @property_name))
    ) @property_setter_def
    (#eq? @decorator_attr "{SETTER_DECORATOR_ATTR}")
    (#eq? @prop_obj @property_name)
    ''',
    regexp_pattern='@{PROPERTY_NAME_PATTERN}\\.{SETTER_ATTR_PATTERN}\\s*\\n\\s*{METHOD_PATTERN}\\s+({IDENTIFIER_PATTERN})\\s*\\(\\s*{FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*:{BODY_CAPTURE_LOOKAHEAD}',
    placeholder_map={
        'python': {
            'NAME_NODE': 'identifier',
            'SETTER_DECORATOR_ATTR': 'setter',
            'PROPERTY_NAME_PATTERN': '([a-zA-Z_][a-zA-Z0-9_]*)', # Capture group for the property name
            'SETTER_ATTR_PATTERN': 'setter',
            'METHOD_PATTERN': 'def',
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*', # This should match the function name, often same as property name
            'FIRST_PARAM_PATTERN': 'self',
            'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
            'BODY_CAPTURE_LOOKAHEAD': '(.*?)(?=\\n(?:[ \\t]*@|[ \\t]*def|\\Z))'
        }
        # Add other languages if needed
    }
)

STATIC_PROPERTY_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.STATIC_PROPERTY,
    description='Static class property (class variable)',
    # CORRECTED: Simplest valid query capturing the class block.
    # Requires Python logic in extractor to filter children.
    tree_sitter_pattern='''
    (class_definition
      body: (block) @class_block
    )
    ''',
    regexp_pattern='{OPTIONAL_NEWLINE_INDENT}({IDENTIFIER_PATTERN}){OPTIONAL_TYPE_HINT}\\s*=\\s*({VALUE_CAPTURE}){OPTIONAL_COMMENT_ENDLINE}',
    placeholder_map={
        'python': {
            'IDENTIFIER_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*',
            'OPTIONAL_NEWLINE_INDENT': '(?:^|\\n)\\s+',
            'OPTIONAL_TYPE_HINT': '(?:\\s*:\\s*[^=]+?)?',
            'VALUE_CAPTURE': '.+?',
            'OPTIONAL_COMMENT_ENDLINE': '(?:$|\\s*#)'
        }
        # Add other languages if needed
    }
)

DECORATOR_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.DECORATOR,
    description='Decorator element',
    tree_sitter_pattern='(decorator) @decorator_node',
    regexp_pattern='{DECORATOR_PREFIX}({QUALIFIED_NAME_PATTERN})(?:{ARGS_PATTERN})?',
    placeholder_map={
        'python': {
            'DECORATOR_PREFIX': '@',
            'QUALIFIED_NAME_PATTERN': '[a-zA-Z_][a-zA-Z0-9_]*(?:\\.[a-zA-Z_][a-zA-Z0-9_]*)*',
            'ARGS_PATTERN': '\\([^)]*\\)' # Optional arguments
        }
        # Add other languages if needed
    }
)

INTERFACE_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.INTERFACE,
    description='Interface definition element',
    tree_sitter_pattern='({INTERFACE_NODE} name: ({NAME_NODE}) @interface_name body: ({BODY_NODE}) @body) @interface_def',
    regexp_pattern='{INTERFACE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)(?:{EXTENDS_PATTERN})?\\s*{BODY_START}', # Adjusted identifier for TS
    placeholder_map={
        'typescript': {
            'INTERFACE_NODE': 'interface_declaration',
            'NAME_NODE': 'type_identifier',
            'BODY_NODE': 'object_type', # Or potentially interface_body depending on grammar version
            'INTERFACE_PATTERN': 'interface',
            'EXTENDS_PATTERN': '(?:\\s+extends\\s+[^{]+)?',
            'BODY_START': '\\s*\\{'
        }
        # Add other languages if needed
    }
)

TYPE_ALIAS_TEMPLATE = ElementTypeTemplate(
    element_type=CodeElementType.TYPE_ALIAS,
    description='Type alias definition element',
    tree_sitter_pattern='({TYPE_NODE} name: ({NAME_NODE}) @type_name) @type_def',
    regexp_pattern='{TYPE_PATTERN}\\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\\s*=', # Adjusted identifier for TS
    placeholder_map={
        'typescript': {
            'TYPE_NODE': 'type_alias_declaration',
            'NAME_NODE': 'type_identifier',
            'TYPE_PATTERN': 'type'
        }
        # Add other languages if needed
    }
)

ELEMENT_TYPE_TEMPLATES: Dict[CodeElementType, ElementTypeTemplate] = {
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
    # Add other templates here
}

def create_element_type_descriptor(language_code: str, element_type: CodeElementType) -> Optional[Dict[str, Any]]:
    """Factory method to create element type descriptor attributes for a language based on templates."""
    template = ELEMENT_TYPE_TEMPLATES.get(element_type)
    if not template:
        logger.debug(f'No template found for element type: {element_type.value}')
        return None

    attributes = template.for_language(language_code)
    if attributes is None:
        logger.warning(f"Template '{element_type.value}' is not configured for language '{language_code}' or pattern generation failed.")
        return None

    # Ensure the element_type from the template is included
    attributes['element_type'] = element_type # Make sure enum object is passed

    return attributes