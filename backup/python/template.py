"""
Tree-sitter query templates for Python code.
"""
from ...models import CodeElementType

TEMPLATES = {
    CodeElementType.CLASS.value: {
        'find_one': '''
        (class_definition
          name: (identifier) @class_name (#eq? @class_name "{class_name}"))
        ''',
        'find_all': '''
        (class_definition
          name: (identifier) @class_name)
        '''
    },
    CodeElementType.METHOD.value: {
        'find_one': '''
        (function_definition
          name: (identifier) @method_name (#eq? @method_name "{method_name}"))
        ''',
        'find_all': '''
        (function_definition
          name: (identifier) @method_name)
        '''
    },
    CodeElementType.FUNCTION.value: {
        'find_one': '''
        (function_definition
          name: (identifier) @func_name (#eq? @func_name "{function_name}"))
        ''',
        'find_all': '''
        (function_definition
          name: (identifier) @func_name)
        '''
    },
    CodeElementType.PROPERTY_GETTER.value: {
        'find_one': '''
        (decorated_definition
          decorator: (decorator
            name: (identifier) @decorator_name (#eq? @decorator_name "property"))
          definition: (function_definition
            name: (identifier) @property_name (#eq? @property_name "{property_name}")))
        ''',
        'find_all': '''
        (decorated_definition
          decorator: (decorator
            name: (identifier) @decorator_name (#eq? @decorator_name "property"))
          definition: (function_definition
            name: (identifier) @property_name))
        '''
    },
    CodeElementType.PROPERTY_SETTER.value: {
        'find_one': '''
        (decorated_definition
          decorator: (decorator
            name: (attribute
              object: (identifier) @prop_obj (#eq? @prop_obj "{property_name}")
              attribute: (identifier) @decorator_attr (#eq? @decorator_attr "setter")))
          definition: (function_definition
            name: (identifier) @property_name (#eq? @property_name "{property_name}")))
        ''',
        'find_all': '''
        (decorated_definition
          decorator: (decorator
            name: (attribute
              object: (identifier)
              attribute: (identifier) @decorator_attr (#eq? @decorator_attr "setter")))
          definition: (function_definition
            name: (identifier) @property_name))
        '''
    },
    CodeElementType.STATIC_PROPERTY.value: {
        'find_one': '''
        (class_definition
          body: (block 
            (expression_statement 
              (assignment 
                left: (identifier) @prop_name (#eq? @prop_name "{property_name}"))))
        ''',
        'find_all': '''
        (class_definition
          body: (block 
            (expression_statement 
              (assignment 
                left: (identifier) @prop_name)))
        '''
    },
    CodeElementType.IMPORT.value: {
        'find_all': '''
        (import_statement) @import
        (import_from_statement) @import
        ''',
        'find_one': '''
        (import_statement) @import
        (import_from_statement) @import
        '''
    },
    "parameters_simple": {
        'find_all': '(parameters (identifier) @param)'
    },
    "parameters_typed": {
        'find_all': '(parameters (typed_parameter name: (identifier) @param_name type: (_) @param_type))'
    },
    "parameters_default": {
        'find_all': '(parameters (default_parameter name: (identifier) @param_name value: (_) @default_value))'
    },
    "parameters_typed_default": {
        'find_all': '(parameters (typed_default_parameter name: (identifier) @param_name type: (_) @param_type value: (_) @default_value))'
    }
}

ADDITIONAL_QUERIES = {
    'instance_property_in_init': '''
    (assignment 
      left: (attribute
        object: (identifier) @self (#eq? @self "self")
        attribute: (identifier) @prop_name (#eq? @prop_name "{property_name}")))
    ''',
    'class_methods': '''
    (class_definition
      name: (identifier) @class_name (#eq? @class_name "{class_name}")
      body: (block 
        (function_definition
          name: (identifier) @method_name)))
    ''',
    'decorated_class': '''
    (decorated_definition
      decorator: (decorator name: (identifier) @decorator_name)
      definition: (class_definition
        name: (identifier) @class_name (#eq? @class_name "{class_name}")))
    ''',
    'decorated_method': '''
    (decorated_definition
      decorator: (decorator name: (identifier) @decorator_name)
      definition: (function_definition
        name: (identifier) @method_name (#eq? @method_name "{method_name}")))
    ''',
    'decorator_for_method': '''
    (decorated_definition
      decorator: (decorator name: (identifier) @decorator_name)
      definition: (function_definition
        name: (identifier) @method_name (#eq? @method_name "{method_name}")))
    ''',
    'language_indicators': {
        'python_class': '(class_definition) @class',
        'python_function': '(function_definition) @function',
        'python_import': '(import_statement) @import',
        'python_import_from': '(import_from_statement) @import_from',
        'python_decorators': '(decorator) @decorator'
    }
}
