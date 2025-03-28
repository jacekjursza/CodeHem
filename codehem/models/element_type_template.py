"""
Element type template system for standardizing language descriptors.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable

@dataclass
class ElementTypeTemplate:
    """Template for creating language-specific element type descriptors."""
    element_type: str
    description: str
    tree_sitter_pattern: str
    regexp_pattern: str
    placeholder_map: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def for_language(self, language_code: str) -> Dict[str, Any]:
        """Generate descriptor attributes for a specific language."""
        placeholders = self.placeholder_map.get(language_code, {})
        tree_sitter_query = self.tree_sitter_pattern
        regexp_pattern = self.regexp_pattern
        for key, value in placeholders.items():
            tree_sitter_query = tree_sitter_query.replace(f'{{{key}}}', value)
            regexp_pattern = regexp_pattern.replace(f'{{{key}}}', value)
        return {'language_code': language_code, 'element_type': self.element_type, 'tree_sitter_query': tree_sitter_query, 'regexp_pattern': regexp_pattern, 'custom_extract': False}

# Define common templates for various element types
CLASS_TEMPLATE = ElementTypeTemplate(
    element_type='class',
    description='Class definition element',
    tree_sitter_pattern='\n    ({CLASS_NODE}\n      name: ({NAME_NODE}) @class_name\n      body: ({BODY_NODE}) @body) @class_def\n    ',
    regexp_pattern='{CLASS_PATTERN}\\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:{INHERITANCE_PATTERN})?\\s*{BODY_START}',
    placeholder_map={
        'python': {
            'CLASS_NODE': 'class_definition',
            'NAME_NODE': 'identifier',
            'BODY_NODE': 'block',
            'CLASS_PATTERN': 'class',
            'INHERITANCE_PATTERN': '\\s*\\([^)]*\\)',
            'BODY_START': ':'
        },
        'typescript': {
            'CLASS_NODE': 'class_declaration',
            'NAME_NODE': 'type_identifier',
            'BODY_NODE': 'class_body',
            'CLASS_PATTERN': 'class',
            'INHERITANCE_PATTERN': '(?:\\s+extends\\s+[a-zA-Z_][a-zA-Z0-9_]*)?(?:\\s+implements\\s+[^{]+)?',
            'BODY_START': '\\s*\\{'
        }
    }
)

METHOD_TEMPLATE = ElementTypeTemplate(
    element_type='method',
    description='Method definition element',
    tree_sitter_pattern='\n    ({METHOD_NODE}\n    name: ({NAME_NODE}) @method_name\n    parameters: ({PARAM_NODE} {FIRST_PARAM_PATTERN}) @first_param\n    body: ({BODY_NODE}) @body) @method_def\n    ',
    regexp_pattern='{METHOD_PATTERN}\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\({FIRST_PARAM_PATTERN}[^)]*\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}',
    placeholder_map={
        'python': {
            'METHOD_NODE': 'function_definition',
            'NAME_NODE': 'identifier',
            'PARAM_NODE': 'parameters',
            'FIRST_PARAM_PATTERN': '(identifier) @first_param (#eq? @first_param "self")',
            'BODY_NODE': 'block',
            'METHOD_PATTERN': 'def',
            'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
            'BODY_START': ':'
        },
        'typescript': {
            'METHOD_NODE': 'method_definition',
            'NAME_NODE': 'property_identifier',
            'PARAM_NODE': 'formal_parameters',
            'FIRST_PARAM_PATTERN': '',
            'BODY_NODE': 'statement_block',
            'METHOD_PATTERN': '',
            'RETURN_TYPE_PATTERN': '(?:\\s*:\\s*[^{]+)?',
            'BODY_START': '\\s*\\{'
        }
    }
)

FUNCTION_TEMPLATE = ElementTypeTemplate(
    element_type='function',
    description='Function definition element',
    tree_sitter_pattern='\n    ({FUNCTION_NODE}\n      name: ({NAME_NODE}) @function_name\n      parameters: ({PARAM_NODE}) @params\n      body: ({BODY_NODE}) @body) @function_def\n    ',
    regexp_pattern='{FUNCTION_PATTERN}\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*\\({PARAMS_PATTERN}\\){RETURN_TYPE_PATTERN}\\s*{BODY_START}',
    placeholder_map={
        'python': {
            'FUNCTION_NODE': 'function_definition',
            'NAME_NODE': 'identifier',
            'PARAM_NODE': 'parameters',
            'BODY_NODE': 'block',
            'FUNCTION_PATTERN': 'def',
            'PARAMS_PATTERN': '(?!.*?self)[^)]*',
            'RETURN_TYPE_PATTERN': '(?:\\s*->.*?)?',
            'BODY_START': ':'
        },
        'typescript': {
            'FUNCTION_NODE': 'function_declaration',
            'NAME_NODE': 'identifier',
            'PARAM_NODE': 'formal_parameters',
            'BODY_NODE': 'statement_block',
            'FUNCTION_PATTERN': 'function',
            'PARAMS_PATTERN': '[^)]*',
            'RETURN_TYPE_PATTERN': '(?:\\s*:\\s*[^{]+)?',
            'BODY_START': '\\s*\\{'
        }
    }
)

# Register all templates
ELEMENT_TYPE_TEMPLATES = {
    'class': CLASS_TEMPLATE,
    'method': METHOD_TEMPLATE,
    'function': FUNCTION_TEMPLATE,
    'import': ElementTypeTemplate(
        element_type='import',
        description='Import statement element',
        tree_sitter_pattern='\n    ({IMPORT_NODE}) @import\n    ',
        regexp_pattern='{IMPORT_PATTERN}',
        placeholder_map={
            'python': {
                'IMPORT_NODE': 'import_statement',
                'IMPORT_PATTERN': '(import\\s+[^\\n;]+|from\\s+[^\\n;]+\\s+import\\s+[^\\n;]+)'
            },
            'typescript': {
                'IMPORT_NODE': 'import_statement',
                'IMPORT_PATTERN': '(import\\s+[^;]+;|export\\s+[^;]+;)'
            }
        }
    ),
    'interface': ElementTypeTemplate(
        element_type='interface',
        description='Interface definition element',
        tree_sitter_pattern='\n    ({INTERFACE_NODE}\n      name: ({NAME_NODE}) @interface_name\n      body: ({BODY_NODE}) @body) @interface_def\n    ',
        regexp_pattern='{INTERFACE_PATTERN}\\s+([a-zA-Z_][a-zA-Z0-9_]*)(?:{EXTENDS_PATTERN})?\\s*{BODY_START}',
        placeholder_map={
            'typescript': {
                'INTERFACE_NODE': 'interface_declaration',
                'NAME_NODE': 'type_identifier',
                'BODY_NODE': 'object_type',
                'INTERFACE_PATTERN': 'interface',
                'EXTENDS_PATTERN': '(?:\\s+extends\\s+[^{]+)?',
                'BODY_START': '\\s*\\{'
            }
        }
    ),
    'type_alias': ElementTypeTemplate(
        element_type='type_alias',
        description='Type alias definition element',
        tree_sitter_pattern='\n    ({TYPE_NODE}\n      name: ({NAME_NODE}) @type_name) @type_def\n    ',
        regexp_pattern='{TYPE_PATTERN}\\s+([a-zA-Z_][a-zA-Z0-9_]*)\\s*=',
        placeholder_map={
            'typescript': {
                'TYPE_NODE': 'type_alias_declaration',
                'NAME_NODE': 'type_identifier',
                'TYPE_PATTERN': 'type'
            }
        }
    )
}

def create_element_type_descriptor(language_code: str, element_type: str) -> Dict[str, Any]:
    """Factory method to create element type descriptor attributes for a language."""
    template = ELEMENT_TYPE_TEMPLATES.get(element_type)
    if not template:
        raise ValueError(f'No template found for element type: {element_type}')
    return template.for_language(language_code)