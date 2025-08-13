"""
TypeScript element extractor component.

This module provides the TypeScript implementation of the IElementExtractor interface,
responsible for extracting different code elements from TypeScript/JavaScript code using Tree-sitter.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from codehem.core.components.interfaces import IElementExtractor, ISyntaxTreeNavigator
from codehem.core.components.base_implementations import BaseElementExtractor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)


class TypeScriptElementExtractor(BaseElementExtractor):
    """
    TypeScript implementation of the IElementExtractor interface.
    
    Extracts various code elements (classes, interfaces, functions, methods, properties, etc.)
    from TypeScript/JavaScript code using Tree-sitter queries.
    """
    
    def __init__(self, navigator: ISyntaxTreeNavigator):
        """
        Initialize the TypeScript element extractor with a syntax tree navigator.
        
        Args:
            navigator: TypeScript syntax tree navigator for executing queries
        """
        super().__init__('typescript', navigator)
    
    def extract_functions(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract function declarations and expressions from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing function data
        """
        logger.debug("Extracting TypeScript functions")
        
        # Query for function declarations, function expressions, and arrow functions
        query_str = """
        (function_declaration
          name: (identifier) @func_name
          parameters: (formal_parameters) @params
          body: (statement_block) @body) @func_decl
        
        (lexical_declaration
          (variable_declarator
            name: (identifier) @func_name
            value: (arrow_function
              parameters: (formal_parameters) @params
              body: (_) @body)) @func_expr) @arrow_func
              
        (export_statement
          (function_declaration
            name: (identifier) @exported_func_name
            parameters: (formal_parameters) @exported_params
            body: (statement_block) @exported_body)) @exported_func
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            functions = []
            
            for match in result:
                func_data = {}
                
                # Handle normal function declarations
                if 'func_name' in match and 'func_decl' in match:
                    func_name = self.navigator.get_node_text(match['func_name'], code_bytes).decode('utf-8')
                    func_node = match['func_decl']
                    params_node = match['params']
                    body_node = match['body']
                    
                    func_range = self.navigator.get_node_range(func_node)
                    
                    func_data = {
                        'name': func_name,
                        'type': CodeElementType.FUNCTION.value,
                        'range': {
                            'start': {'line': func_range[0], 'column': 0},
                            'end': {'line': func_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(func_node, code_bytes).decode('utf-8'),
                        'parameters': self._extract_parameters(params_node, code_bytes, False)
                    }
                    
                # Handle exported function declarations
                elif 'exported_func_name' in match and 'exported_func' in match:
                    func_name = self.navigator.get_node_text(match['exported_func_name'], code_bytes).decode('utf-8')
                    func_node = match['exported_func']
                    params_node = match['exported_params']
                    body_node = match['exported_body']
                    
                    func_range = self.navigator.get_node_range(func_node)
                    
                    func_data = {
                        'name': func_name,
                        'type': CodeElementType.FUNCTION.value,
                        'range': {
                            'start': {'line': func_range[0], 'column': 0},
                            'end': {'line': func_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(func_node, code_bytes).decode('utf-8'),
                        'parameters': self._extract_parameters(params_node, code_bytes, False),
                        'additional_data': {'is_exported': True}
                    }
                
                # Handle arrow functions
                elif 'func_name' in match and 'arrow_func' in match:
                    func_name = self.navigator.get_node_text(match['func_name'], code_bytes).decode('utf-8')
                    func_node = match['arrow_func']
                    params_node = match['params']
                    body_node = match['body']
                    
                    func_range = self.navigator.get_node_range(func_node)
                    
                    func_data = {
                        'name': func_name,
                        'type': CodeElementType.FUNCTION.value,
                        'range': {
                            'start': {'line': func_range[0], 'column': 0},
                            'end': {'line': func_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(func_node, code_bytes).decode('utf-8'),
                        'parameters': self._extract_parameters(params_node, code_bytes, False),
                        'additional_data': {'is_arrow_function': True}
                    }
                
                if func_data:
                    functions.append(func_data)
            
            logger.debug(f"Found {len(functions)} TypeScript functions")
            return functions
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript functions: {e}", exc_info=True)
            return []
    
    def extract_classes(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract class declarations from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing class data
        """
        logger.debug("Extracting TypeScript classes")
        
        query_str = """
        (class_declaration
          name: (type_identifier) @class_name
          body: (class_body) @body) @class_decl
          
        (export_statement
          (class_declaration
            name: (type_identifier) @exported_class_name
            body: (class_body) @exported_body)) @exported_class
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            classes = []
            
            for match in result:
                class_data = {}
                
                # Handle normal class declarations
                if 'class_name' in match and 'class_decl' in match:
                    class_name = self.navigator.get_node_text(match['class_name'], code_bytes).decode('utf-8')
                    class_node = match['class_decl']
                    body_node = match['body']
                    
                    class_range = self.navigator.get_node_range(class_node)
                    
                    class_data = {
                        'name': class_name,
                        'type': CodeElementType.CLASS.value,
                        'range': {
                            'start': {'line': class_range[0], 'column': 0},
                            'end': {'line': class_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(class_node, code_bytes).decode('utf-8')
                    }
                
                # Handle exported class declarations
                elif 'exported_class_name' in match and 'exported_class' in match:
                    class_name = self.navigator.get_node_text(match['exported_class_name'], code_bytes).decode('utf-8')
                    class_node = match['exported_class']
                    body_node = match['exported_body']
                    
                    class_range = self.navigator.get_node_range(class_node)
                    
                    class_data = {
                        'name': class_name,
                        'type': CodeElementType.CLASS.value,
                        'range': {
                            'start': {'line': class_range[0], 'column': 0},
                            'end': {'line': class_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(class_node, code_bytes).decode('utf-8'),
                        'additional_data': {'is_exported': True}
                    }
                
                if class_data:
                    classes.append(class_data)
            
            logger.debug(f"Found {len(classes)} TypeScript classes")
            return classes
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript classes: {e}", exc_info=True)
            return []
    
    def extract_methods(self, tree: Any, code_bytes: bytes, class_name: Optional[str] = None) -> List[Dict]:
        """
        Extract methods from TypeScript classes.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            class_name: Optional name of a specific class to extract methods from
            
        Returns:
            List of dictionaries containing method data
        """
        logger.debug(f"Extracting TypeScript methods" + (f" for class {class_name}" if class_name else ""))
        
        query_str = """
        (class_declaration
          name: (type_identifier) @class_name
          body: (class_body
            (method_definition
              name: (property_identifier) @method_name) @method_def))
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            methods = []
            
            # Extract class name from the first match that has it
            current_class_name = None
            for match in result:
                if 'class_name' in match:
                    current_class_name = self.navigator.get_node_text(match['class_name'], code_bytes).decode('utf-8')
                    break
            
            # Filter by class name if specified
            if class_name and current_class_name and current_class_name != class_name:
                return methods
            
            for match in result:
                if 'method_name' in match and 'method_def' in match:
                    method_name = self.navigator.get_node_text(match['method_name'], code_bytes).decode('utf-8')
                    method_node = match['method_def']
                    
                    # Find parameters and body within the method node
                    params_node = None
                    body_node = None
                    for child in method_node.children:
                        if child.type == 'formal_parameters':
                            params_node = child
                        elif child.type == 'statement_block':
                            body_node = child
                    
                    method_range = self.navigator.get_node_range(method_node)
                    
                    method_data = {
                        'name': method_name,
                        'class_name': current_class_name or 'Unknown',
                        'type': CodeElementType.METHOD.value,
                        'range': {
                            'start': {'line': method_range[0], 'column': 0},
                            'end': {'line': method_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(method_node, code_bytes).decode('utf-8'),
                        'parameters': self._extract_parameters(params_node, code_bytes, True) if params_node else []
                    }
                    
                    methods.append(method_data)
            
            logger.debug(f"Found {len(methods)} TypeScript methods")
            return methods
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript methods: {e}", exc_info=True)
            return []
    
    def extract_properties(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract properties (class fields) from TypeScript classes.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing property data
        """
        logger.debug("Extracting TypeScript properties")
        
        # Query for all public field definitions and get class context separately
        query_str = """
        (public_field_definition
          name: (property_identifier) @prop_name
          type: (type_annotation)? @type_annotation
          value: (_)? @value) @prop_def
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            properties = []
            
            for match in result:
                if 'prop_name' in match and 'prop_def' in match:
                    prop_name = self.navigator.get_node_text(match['prop_name'], code_bytes).decode('utf-8')
                    prop_node = match['prop_def']
                    
                    # Find the parent class of this property
                    class_node = self.navigator.find_parent_of_type(prop_node, 'class_declaration')
                    if not class_node:
                        continue
                    
                    # Get class name
                    class_query = "(class_declaration name: (type_identifier) @class_name)"
                    class_result = self.navigator.execute_query(class_node, code_bytes, class_query)
                    
                    class_name = None
                    if class_result and 'class_name' in class_result[0]:
                        class_name = self.navigator.get_node_text(class_result[0]['class_name'], code_bytes).decode('utf-8')
                    
                    if not class_name:
                        continue
                    
                    prop_range = self.navigator.get_node_range(prop_node)
                    
                    # Extract type annotation if available
                    value_type = None
                    if 'type_annotation' in match and match['type_annotation'] is not None:
                        type_node = match['type_annotation']
                        type_text = self.navigator.get_node_text(type_node, code_bytes).decode('utf-8')
                        # Remove the leading colon if present
                        value_type = type_text.lstrip(':').strip()
                    
                    # Extract value if available
                    value = None
                    if 'value' in match and match['value'] is not None:
                        value_node = match['value']
                        value = self.navigator.get_node_text(value_node, code_bytes).decode('utf-8')
                    
                    property_data = {
                        'name': prop_name,
                        'class_name': class_name,
                        'type': CodeElementType.PROPERTY.value,
                        'range': {
                            'start': {'line': prop_range[0], 'column': 0},
                            'end': {'line': prop_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(prop_node, code_bytes).decode('utf-8'),
                        'value_type': value_type,
                        'additional_data': {}
                    }
                    
                    if value:
                        property_data['additional_data']['value'] = value
                    
                    properties.append(property_data)
            
            logger.debug(f"Found {len(properties)} TypeScript properties")
            return properties
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript properties: {e}", exc_info=True)
            return []
    
    def extract_static_properties(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract static properties from TypeScript classes.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing static property data
        """
        logger.debug("Extracting TypeScript static properties")
        
        query_str = """
        (class_declaration
          name: (type_identifier) @class_name
          body: (class_body
            (public_field_definition
              name: (property_identifier) @static_prop_name
              type: (type_annotation)? @type_annotation
              value: (_)? @value))) @static_prop_def
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            static_properties = []
            
            for match in result:
                if 'class_name' in match and 'static_prop_name' in match and 'static_prop_def' in match:
                    class_name = self.navigator.get_node_text(match['class_name'], code_bytes).decode('utf-8')
                    prop_name = self.navigator.get_node_text(match['static_prop_name'], code_bytes).decode('utf-8')
                    prop_node = match['static_prop_def']
                    
                    prop_range = self.navigator.get_node_range(prop_node)
                    
                    # Extract type annotation if available
                    value_type = None
                    if 'type_annotation' in match and match['type_annotation'] is not None:
                        type_node = match['type_annotation']
                        type_text = self.navigator.get_node_text(type_node, code_bytes).decode('utf-8')
                        # Remove the leading colon if present
                        value_type = type_text.lstrip(':').strip()
                    
                    # Extract value if available
                    value = None
                    if 'value' in match and match['value'] is not None:
                        value_node = match['value']
                        value = self.navigator.get_node_text(value_node, code_bytes).decode('utf-8')
                    
                    property_data = {
                        'name': prop_name,
                        'class_name': class_name,
                        'type': CodeElementType.STATIC_PROPERTY.value,
                        'range': {
                            'start': {'line': prop_range[0], 'column': 0},
                            'end': {'line': prop_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(prop_node, code_bytes).decode('utf-8'),
                        'value_type': value_type,
                        'additional_data': {'is_static': True}
                    }
                    
                    if value:
                        property_data['additional_data']['value'] = value
                    
                    static_properties.append(property_data)
            
            logger.debug(f"Found {len(static_properties)} TypeScript static properties")
            return static_properties
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript static properties: {e}", exc_info=True)
            return []
    
    def extract_imports(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract import statements from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing import data
        """
        logger.debug("Extracting TypeScript imports")
        
        query_str = """
        (import_statement) @import
        (import_clause) @import_clause
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            imports = []
            
            import_nodes = []
            for match in result:
                if 'import' in match:
                    import_node = match['import']
                    import_nodes.append(import_node)
            
            import re
            for import_node in import_nodes:
                import_range = self.navigator.get_node_range(import_node)
                import_text = self.navigator.get_node_text(import_node, code_bytes).decode('utf-8')
                # Parse module and aliases
                module_name = None
                side_effect = False
                m_from = re.search(r"from\s+['\"]([^'\"]+)['\"]", import_text)
                if m_from:
                    module_name = m_from.group(1)
                else:
                    m_se = re.match(r"\s*import\s+['\"]([^'\"]+)['\"]", import_text)
                    if m_se:
                        module_name = m_se.group(1)
                        side_effect = True
                # Default alias
                default_alias = None
                m_def = re.match(r"\s*import\s+([A-Za-z_$][\w$]*)\s*(?:,|from)\s*", import_text)
                if m_def and not re.search(r"import\s*\*\s*as\s+", import_text):
                    default_alias = m_def.group(1)
                # Namespace alias
                ns_alias = None
                m_ns = re.search(r"import\s*\*\s*as\s+([A-Za-z_$][\w$]*)", import_text)
                if m_ns:
                    ns_alias = m_ns.group(1)
                # Named specifiers
                from_aliases = []
                names = []
                m_named = re.search(r"\{([^}]*)\}", import_text)
                if m_named:
                    inner = m_named.group(1)
                    for part in [p.strip() for p in inner.split(',') if p.strip()]:
                        if ' as ' in part:
                            nm, al = [x.strip() for x in part.split(' as ', 1)]
                            from_aliases.append({'name': nm, 'alias': al})
                            names.append(nm)
                        else:
                            from_aliases.append({'name': part, 'alias': part})
                            names.append(part)
                aliases = []
                if ns_alias and module_name:
                    aliases.append({'module': module_name, 'alias': ns_alias})
                if default_alias and module_name:
                    aliases.append({'module': module_name, 'alias': default_alias})

                import_data = {
                    'name': self._get_import_name(import_text),
                    'type': CodeElementType.IMPORT.value,
                    'range': {
                        'start': {'line': import_range[0], 'column': 0},
                        'end': {'line': import_range[1], 'column': 0}
                    },
                    'content': import_text,
                    'additional_data': {
                        'module': module_name,
                        'side_effect': side_effect,
                        'aliases': aliases,
                        'from_aliases': from_aliases,
                        'names': names,
                    }
                }

                imports.append(import_data)
            
            logger.debug(f"Found {len(imports)} TypeScript imports")
            return imports
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript imports: {e}", exc_info=True)
            return []
    
    def extract_interfaces(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract interface declarations from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing interface data
        """
        logger.debug("Extracting TypeScript interfaces")
        
        query_str = """
        (interface_declaration
          name: (type_identifier) @interface_name
          body: (interface_body) @body) @interface_decl
          
        (export_statement
          (interface_declaration
            name: (type_identifier) @exported_interface_name
            body: (interface_body) @exported_body)) @exported_interface
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            interfaces = []
            
            for match in result:
                interface_data = {}
                
                # Handle normal interface declarations
                if 'interface_name' in match and 'interface_decl' in match:
                    interface_name = self.navigator.get_node_text(match['interface_name'], code_bytes).decode('utf-8')
                    interface_node = match['interface_decl']
                    body_node = match['body']
                    
                    interface_range = self.navigator.get_node_range(interface_node)
                    
                    interface_data = {
                        'name': interface_name,
                        'type': CodeElementType.INTERFACE.value,
                        'range': {
                            'start': {'line': interface_range[0], 'column': 0},
                            'end': {'line': interface_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(interface_node, code_bytes).decode('utf-8')
                    }
                
                # Handle exported interface declarations
                elif 'exported_interface_name' in match and 'exported_interface' in match:
                    interface_name = self.navigator.get_node_text(match['exported_interface_name'], code_bytes).decode('utf-8')
                    interface_node = match['exported_interface']
                    body_node = match['exported_body']
                    
                    interface_range = self.navigator.get_node_range(interface_node)
                    
                    interface_data = {
                        'name': interface_name,
                        'type': CodeElementType.INTERFACE.value,
                        'range': {
                            'start': {'line': interface_range[0], 'column': 0},
                            'end': {'line': interface_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(interface_node, code_bytes).decode('utf-8'),
                        'additional_data': {'is_exported': True}
                    }
                
                if interface_data:
                    interfaces.append(interface_data)
            
            logger.debug(f"Found {len(interfaces)} TypeScript interfaces")
            return interfaces
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript interfaces: {e}", exc_info=True)
            return []

    def extract_decorators(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract decorators from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing decorator data
        """
        logger.debug("Extracting TypeScript decorators")
        
        query_str = """
        (decorator
          "@" @at_symbol
          (call_expression
            function: (identifier) @decorator_name
            arguments: (arguments)? @args)) @decorator
            
        (decorator
          "@" @at_symbol  
          (identifier) @decorator_name) @decorator
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            decorators = []
            
            for match in result:
                if 'decorator' in match and 'decorator_name' in match:
                    decorator_node = match['decorator']
                    decorator_name = self.navigator.get_node_text(match['decorator_name'], code_bytes).decode('utf-8')
                    
                    decorator_range = self.navigator.get_node_range(decorator_node)
                    decorator_text = self.navigator.get_node_text(decorator_node, code_bytes).decode('utf-8')
                    
                    # Try to determine the parent element
                    parent_node = self._find_decorator_parent(decorator_node, tree, code_bytes)
                    parent_name = None
                    if parent_node:
                        parent_name = self._get_parent_name(parent_node, code_bytes)
                    
                    # Extract arguments if available
                    args = None
                    if 'args' in match and match['args'] is not None:
                        args_node = match['args']
                        args = self.navigator.get_node_text(args_node, code_bytes).decode('utf-8')
                    
                    decorator_data = {
                        'name': decorator_name,
                        'type': CodeElementType.DECORATOR.value,
                        'range': {
                            'start': {'line': decorator_range[0], 'column': 0},
                            'end': {'line': decorator_range[1], 'column': 0}
                        },
                        'content': decorator_text,
                        'parent_name': parent_name,
                        'additional_data': {}
                    }
                    
                    if args:
                        decorator_data['additional_data']['arguments'] = args
                    
                    decorators.append(decorator_data)
            
            logger.debug(f"Found {len(decorators)} TypeScript decorators")
            return decorators
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript decorators: {e}", exc_info=True)
            return []
    
    def extract_enums(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract enum declarations from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing enum data
        """
        logger.debug("Extracting TypeScript enums")
        
        query_str = """
        (enum_declaration
          (identifier) @enum_name
          (enum_body) @body) @enum_decl
          
        (export_statement
          (enum_declaration
            (identifier) @exported_enum_name
            (enum_body) @exported_body)) @exported_enum
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            enums = []
            
            for match in result:
                enum_data = {}
                
                # Handle normal enum declarations
                if 'enum_name' in match and 'enum_decl' in match:
                    enum_name = self.navigator.get_node_text(match['enum_name'], code_bytes).decode('utf-8')
                    enum_node = match['enum_decl']
                    body_node = match['body']
                    
                    enum_range = self.navigator.get_node_range(enum_node)
                    
                    enum_data = {
                        'name': enum_name,
                        'type': CodeElementType.ENUM.value,
                        'range': {
                            'start': {'line': enum_range[0], 'column': 0},
                            'end': {'line': enum_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(enum_node, code_bytes).decode('utf-8')
                    }
                
                # Handle exported enum declarations
                elif 'exported_enum_name' in match and 'exported_enum' in match:
                    enum_name = self.navigator.get_node_text(match['exported_enum_name'], code_bytes).decode('utf-8')
                    enum_node = match['exported_enum']
                    body_node = match['exported_body']
                    
                    enum_range = self.navigator.get_node_range(enum_node)
                    
                    enum_data = {
                        'name': enum_name,
                        'type': CodeElementType.ENUM.value,
                        'range': {
                            'start': {'line': enum_range[0], 'column': 0},
                            'end': {'line': enum_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(enum_node, code_bytes).decode('utf-8'),
                        'additional_data': {'is_exported': True}
                    }
                
                if enum_data:
                    enums.append(enum_data)
            
            logger.debug(f"Found {len(enums)} TypeScript enums")
            return enums
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript enums: {e}", exc_info=True)
            return []
    
    def extract_type_aliases(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract type alias declarations from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing type alias data
        """
        logger.debug("Extracting TypeScript type aliases")
        
        query_str = """
        (type_alias_declaration
          name: (type_identifier) @type_name
          value: (_) @value) @type_alias
          
        (export_statement
          (type_alias_declaration
            name: (type_identifier) @exported_type_name
            value: (_) @exported_value)) @exported_type_alias
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            type_aliases = []
            
            for match in result:
                type_data = {}
                
                # Handle normal type alias declarations
                if 'type_name' in match and 'type_alias' in match:
                    type_name = self.navigator.get_node_text(match['type_name'], code_bytes).decode('utf-8')
                    type_node = match['type_alias']
                    value_node = match['value']
                    
                    type_range = self.navigator.get_node_range(type_node)
                    
                    type_data = {
                        'name': type_name,
                        'type': CodeElementType.TYPE_ALIAS.value,
                        'range': {
                            'start': {'line': type_range[0], 'column': 0},
                            'end': {'line': type_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(type_node, code_bytes).decode('utf-8'),
                        'value': self.navigator.get_node_text(value_node, code_bytes).decode('utf-8')
                    }
                
                # Handle exported type alias declarations
                elif 'exported_type_name' in match and 'exported_type_alias' in match:
                    type_name = self.navigator.get_node_text(match['exported_type_name'], code_bytes).decode('utf-8')
                    type_node = match['exported_type_alias']
                    value_node = match['exported_value']
                    
                    type_range = self.navigator.get_node_range(type_node)
                    
                    type_data = {
                        'name': type_name,
                        'type': CodeElementType.TYPE_ALIAS.value,
                        'range': {
                            'start': {'line': type_range[0], 'column': 0},
                            'end': {'line': type_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(type_node, code_bytes).decode('utf-8'),
                        'value': self.navigator.get_node_text(value_node, code_bytes).decode('utf-8'),
                        'additional_data': {'is_exported': True}
                    }
                
                if type_data:
                    type_aliases.append(type_data)
            
            logger.debug(f"Found {len(type_aliases)} TypeScript type aliases")
            return type_aliases
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript type aliases: {e}", exc_info=True)
            return []
    
    def extract_namespaces(self, tree: Any, code_bytes: bytes) -> List[Dict]:
        """
        Extract namespace declarations from TypeScript code.
        
        Args:
            tree: The parsed syntax tree
            code_bytes: The original code bytes
            
        Returns:
            List of dictionaries containing namespace data
        """
        logger.debug("Extracting TypeScript namespaces")
        
        query_str = """
        (internal_module
          (identifier) @namespace_name
          (statement_block) @body) @namespace_decl
          
        (export_statement
          (internal_module
            (identifier) @exported_namespace_name
            (statement_block) @exported_body)) @exported_namespace
        """
        
        try:
            result = self.navigator.execute_query(tree, code_bytes, query_str)
            namespaces = []
            
            for match in result:
                namespace_data = {}
                
                # Handle normal namespace declarations
                if 'namespace_name' in match and 'namespace_decl' in match:
                    namespace_name = self.navigator.get_node_text(match['namespace_name'], code_bytes).decode('utf-8')
                    namespace_node = match['namespace_decl']
                    body_node = match['body']
                    
                    namespace_range = self.navigator.get_node_range(namespace_node)
                    
                    namespace_data = {
                        'name': namespace_name,
                        'type': CodeElementType.NAMESPACE.value,
                        'range': {
                            'start': {'line': namespace_range[0], 'column': 0},
                            'end': {'line': namespace_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(namespace_node, code_bytes).decode('utf-8')
                    }
                
                # Handle exported namespace declarations
                elif 'exported_namespace_name' in match and 'exported_namespace' in match:
                    namespace_name = self.navigator.get_node_text(match['exported_namespace_name'], code_bytes).decode('utf-8')
                    namespace_node = match['exported_namespace']
                    body_node = match['exported_body']
                    
                    namespace_range = self.navigator.get_node_range(namespace_node)
                    
                    namespace_data = {
                        'name': namespace_name,
                        'type': CodeElementType.NAMESPACE.value,
                        'range': {
                            'start': {'line': namespace_range[0], 'column': 0},
                            'end': {'line': namespace_range[1], 'column': 0}
                        },
                        'content': self.navigator.get_node_text(namespace_node, code_bytes).decode('utf-8'),
                        'additional_data': {'is_exported': True}
                    }
                
                if namespace_data:
                    namespaces.append(namespace_data)
            
            logger.debug(f"Found {len(namespaces)} TypeScript namespaces")
            return namespaces
            
        except Exception as e:
            logger.error(f"Error extracting TypeScript namespaces: {e}", exc_info=True)
            return []
    
    def _extract_parameters(self, params_node: Any, code_bytes: bytes, is_method: bool = False) -> List[Dict]:
        """
        Extract parameters from a formal parameters node.
        
        Args:
            params_node: The formal parameters node
            code_bytes: The original code bytes
            is_method: Whether the parameters belong to a method (affects 'this' handling)
            
        Returns:
            List of dictionaries containing parameter data
        """
        if not params_node:
            return []
        
        try:
            # Query to extract individual parameters
            query_str = """
            (formal_parameters
              (required_parameter
                name: (identifier) @param_name
                type: (type_annotation)? @type_annotation)) @required_param
                
            (formal_parameters
              (optional_parameter
                name: (identifier) @opt_param_name
                type: (type_annotation)? @opt_type_annotation
                value: (_)? @default_value)) @optional_param
            """
            
            result = self.navigator.execute_query(params_node, code_bytes, query_str)
            parameters = []
            
            for match in result:
                param_data = {}
                
                # Handle required parameters
                if 'param_name' in match and 'required_param' in match:
                    param_name = self.navigator.get_node_text(match['param_name'], code_bytes).decode('utf-8')
                    param_node = match['required_param']
                    
                    param_data = {
                        'name': param_name,
                        'optional': False
                    }
                    
                    # Extract type annotation if available
                    if 'type_annotation' in match and match['type_annotation'] is not None:
                        type_node = match['type_annotation']
                        type_text = self.navigator.get_node_text(type_node, code_bytes).decode('utf-8')
                        # Remove the leading colon if present
                        param_data['type'] = type_text.lstrip(':').strip()
                
                # Handle optional parameters
                elif 'opt_param_name' in match and 'optional_param' in match:
                    param_name = self.navigator.get_node_text(match['opt_param_name'], code_bytes).decode('utf-8')
                    param_node = match['optional_param']
                    
                    param_data = {
                        'name': param_name,
                        'optional': True
                    }
                    
                    # Extract type annotation if available
                    if 'opt_type_annotation' in match and match['opt_type_annotation'] is not None:
                        type_node = match['opt_type_annotation']
                        type_text = self.navigator.get_node_text(type_node, code_bytes).decode('utf-8')
                        # Remove the leading colon if present
                        param_data['type'] = type_text.lstrip(':').strip()
                    
                    # Extract default value if available
                    if 'default_value' in match and match['default_value'] is not None:
                        value_node = match['default_value']
                        param_data['default'] = self.navigator.get_node_text(value_node, code_bytes).decode('utf-8')
                
                if param_data:
                    parameters.append(param_data)
            
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {e}", exc_info=True)
            return []
    
    def _get_import_name(self, import_text: str) -> str:
        """
        Extract a representative name from an import statement.
        
        Args:
            import_text: The text of the import statement
            
        Returns:
            A representative name for the import
        """
        # Extract the module name from the import statement
        # e.g., "import { Component } from 'react';" -> "react"
        #       "import React from 'react';" -> "react"
        try:
            # Look for text between single or double quotes
            import_parts = import_text.split("'")
            if len(import_parts) >= 3:
                return import_parts[1]
            
            import_parts = import_text.split('"')
            if len(import_parts) >= 3:
                return import_parts[1]
            
            # If no module name can be extracted, use a generic name
            return "import-statement"
            
        except Exception:
            return "import-statement"
    
    def _find_decorator_parent(self, decorator_node: Any, tree: Any, code_bytes: bytes) -> Optional[Any]:
        """
        Find the parent element (class, method, property) of a decorator.
        
        Args:
            decorator_node: The decorator node
            tree: The complete syntax tree
            code_bytes: The original code bytes
            
        Returns:
            The parent node or None if not found
        """
        try:
            # The parent element should be the sibling of the decorator
            decorator_line = self.navigator.get_node_range(decorator_node)[0]
            
            # Define potential parent types
            parent_types = [
                'class_declaration',
                'method_definition',
                'public_field_definition'
            ]
            
            # Query for potential parents - run separate queries to avoid conflicts
            all_parents = []
            for parent_type in parent_types:
                query_str = f"({parent_type}) @parent"
                result = self.navigator.execute_query(tree, code_bytes, query_str)
                all_parents.extend(result)
            
            closest_parent = None
            min_distance = float('inf')
            
            for match in all_parents:
                if 'parent' in match:
                    parent_node = match['parent']
                    parent_range = self.navigator.get_node_range(parent_node)
                    
                    # The parent should be after the decorator
                    if parent_range[0] > decorator_line:
                        distance = parent_range[0] - decorator_line
                        
                        # Find the closest parent
                        if distance < min_distance:
                            min_distance = distance
                            closest_parent = parent_node
            
            return closest_parent
            
        except Exception as e:
            logger.error(f"Error finding decorator parent: {e}", exc_info=True)
            return None
    
    def _get_parent_name(self, parent_node: Any, code_bytes: bytes) -> Optional[str]:
        """
        Extract the name of a parent element (class, method, property).
        
        Args:
            parent_node: The parent node
            code_bytes: The original code bytes
            
        Returns:
            The name of the parent element or None if not found
        """
        try:
            node_type = parent_node.type
            
            # Different parent types have different structures for names
            if node_type == 'class_declaration':
                # Query for class name
                query_str = "(class_declaration name: (type_identifier) @class_name)"
                
            elif node_type == 'method_definition':
                # For method definitions, we need to get the class name too
                # First get the method name
                query_str = "(method_definition name: (property_identifier) @method_name)"
                result = self.navigator.execute_query(parent_node, code_bytes, query_str)
                
                method_name = None
                for match in result:
                    if 'method_name' in match and match['method_name']:
                        method_name = self.navigator.get_node_text(match['method_name'], code_bytes).decode('utf-8')
                        break
                
                if not method_name:
                    return None
                
                # Find the parent class
                class_node = self.navigator.find_parent_of_type(parent_node, 'class_declaration')
                if class_node:
                    class_query = "(class_declaration name: (type_identifier) @class_name)"
                    class_result = self.navigator.execute_query(class_node, code_bytes, class_query)
                    
                    for match in class_result:
                        if 'class_name' in match and match['class_name']:
                            class_name = self.navigator.get_node_text(match['class_name'], code_bytes).decode('utf-8')
                            return f"{class_name}.{method_name}"
                
                # If no class found, just return method name
                return method_name
                
            elif node_type == 'public_field_definition':
                # Query for property name
                query_str = "(public_field_definition name: (property_identifier) @prop_name)"
                
            else:
                return None
            
            # This code only executes for class_declaration and public_field_definition
            result = self.navigator.execute_query(parent_node, code_bytes, query_str)
            
            for match in result:
                name_key = None
                for key in match.keys():
                    if key.endswith('_name'):
                        name_key = key
                        break
                
                if name_key and match[name_key]:
                    name_node = match[name_key]
                    return self.navigator.get_node_text(name_node, code_bytes).decode('utf-8')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting parent name: {e}", exc_info=True)
            return None
