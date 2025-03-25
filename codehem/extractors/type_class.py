"""
Generic class extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class ClassExtractor(BaseExtractor):
    """Class extractor using language-specific handlers."""
    ELEMENT_TYPE = CodeElementType.CLASS

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return self.ELEMENT_TYPE

    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        return language_code.lower() in self.handlers

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract classes from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted classes as dictionaries
        """
        context = context or {}
        language_code = context.get('language_code', 'python').lower()
        if not self.supports_language(language_code):
            return []
        handler = self.handlers[language_code]
        if handler.custom_extract:
            return handler.extract(code, context)
        return self._extract_with_patterns(code, handler, context)

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            classes = self._extract_with_tree_sitter(code, handler, context)
            if classes:
                return classes
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract classes using TreeSitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
        try:
            (root, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            classes = []

            # Track classes by name to collect their information
            class_nodes = {}

            # First pass: collect all the classes and their names
            for (node, capture_name) in query_results:
                if capture_name == 'class_def':
                    class_def = node
                    name_node = ast_handler.find_child_by_field_name(class_def, 'name')
                    if name_node:
                        class_name = ast_handler.get_node_text(name_node, code_bytes)
                        class_nodes[class_name] = class_def
                elif capture_name == 'class_name':
                    class_name = ast_handler.get_node_text(node, code_bytes)
                    parent_node = ast_handler.find_parent_of_type(node, 'class_definition')
                    if parent_node:
                        class_nodes[class_name] = parent_node

            # Second pass: process each class
            for class_name, class_def in class_nodes.items():
                content = ast_handler.get_node_text(class_def, code_bytes)
                decorators = self._extract_decorators(class_def, code_bytes, ast_handler)
                methods = self._extract_methods(class_def, code_bytes, ast_handler, class_name)
                properties = self._extract_properties(class_def, code_bytes, ast_handler)
                static_properties = self._extract_static_properties(class_def, code_bytes, ast_handler, class_name)

                classes.append({
                    'type': 'class',
                    'name': class_name,
                    'content': content,
                    'range': {
                        'start': {'line': class_def.start_point[0], 'column': class_def.start_point[1]},
                        'end': {'line': class_def.end_point[0], 'column': class_def.end_point[1]}
                    },
                    'decorators': decorators,
                    'members': {
                        'methods': methods,
                        'properties': properties,
                        'static_properties': static_properties
                    }
                })

            return classes
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return []
    
    def _extract_decorators(self, class_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract decorators from a class node.
        
        Args:
            class_node: Class node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of decorator dictionaries
        """
        decorators = []
        parent_node = class_node.parent
        
        if parent_node and parent_node.type == 'decorated_definition':
            for child_idx in range(parent_node.named_child_count):
                child = parent_node.named_child(child_idx)
                if child.type == 'decorator':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        decorator_name = ast_handler.get_node_text(name_node, code_bytes)
                        decorator_content = ast_handler.get_node_text(child, code_bytes)
                        
                        decorators.append({
                            'name': decorator_name,
                            'content': decorator_content
                        })
        
        return decorators

    def _extract_methods(self, class_node, code_bytes, ast_handler, class_name) -> List[Dict]:
        """
        Extract methods from a class node.
        
        Args:
            class_node: Class node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            class_name: Name of the class
            
        Returns:
            List of method dictionaries
        """
        methods = []
        
        # Find the class body
        body_node = class_node.child_by_field_name('body')
        if not body_node:
            return methods
        
        # Query for all function definitions in the class body
        method_query = "(function_definition name: (identifier) @method_name) @method_def"
        method_results = ast_handler.execute_query(method_query, body_node, code_bytes)
        
        for (node, node_type) in method_results:
            if node_type == 'method_name':
                method_name = ast_handler.get_node_text(node, code_bytes)
                method_node = ast_handler.find_parent_of_type(node, 'function_definition')
                if method_node:
                    # Check if this is a method (has self/cls parameter)
                    is_method = False
                    params_node = method_node.child_by_field_name('parameters')
                    if params_node and params_node.named_child_count > 0:
                        first_param = params_node.named_child(0)
                        if first_param.type == 'identifier':
                            first_param_name = ast_handler.get_node_text(first_param, code_bytes)
                            is_method = first_param_name in ['self', 'cls']
                    
                    if is_method:
                        # Get method decorators
                        decorators = []
                        parent_node = method_node.parent
                        if parent_node and parent_node.type == 'decorated_definition':
                            for child_idx in range(parent_node.named_child_count):
                                child = parent_node.named_child(child_idx)
                                if child.type == 'decorator':
                                    name_node = child.child_by_field_name('name')
                                    if name_node:
                                        dec_name = ast_handler.get_node_text(name_node, code_bytes)
                                        dec_content = ast_handler.get_node_text(child, code_bytes)
                                        decorators.append({
                                            'name': dec_name,
                                            'content': dec_content
                                        })
                            
                            # If decorated, use the decorated definition's range
                            start_line = parent_node.start_point[0]
                            end_line = parent_node.end_point[0]
                            method_content = ast_handler.get_node_text(parent_node, code_bytes)
                        else:
                            start_line = method_node.start_point[0]
                            end_line = method_node.end_point[0]
                            method_content = ast_handler.get_node_text(method_node, code_bytes)
                        
                        # Extract parameters
                        parameters = []
                        if params_node:
                            for i in range(params_node.named_child_count):
                                if i == 0 and is_method:  # Skip self/cls
                                    continue
                                    
                                param_node = params_node.named_child(i)
                                param_info = self._extract_parameter(param_node, code_bytes, ast_handler)
                                if param_info:
                                    parameters.append(param_info)
                        
                        # Extract return type
                        return_type = None
                        return_type_node = method_node.child_by_field_name('return_type')
                        if return_type_node:
                            return_type = ast_handler.get_node_text(return_type_node, code_bytes)
                        
                        # Determine if this is a property getter/setter
                        method_type = 'method'
                        property_name = None
                        
                        for decorator in decorators:
                            if decorator['name'] == 'property':
                                method_type = 'property_getter'
                                property_name = method_name
                            elif '.' in decorator['name'] and decorator['name'].endswith('.setter'):
                                method_type = 'property_setter'
                                property_name = decorator['name'].split('.')[0]
                        
                        methods.append({
                            'type': method_type,
                            'name': method_name,
                            'content': method_content,
                            'class_name': class_name,
                            'range': {
                                'start': {'line': start_line, 'column': method_node.start_point[1]},
                                'end': {'line': end_line, 'column': method_node.end_point[1]}
                            },
                            'decorators': decorators,
                            'parameters': parameters,
                            'return_type': return_type,
                            'property_name': property_name
                        })
        
        return methods
    
    def _extract_parameter(self, param_node, code_bytes, ast_handler) -> Optional[Dict]:
        """
        Extract information about a parameter.
        
        Args:
            param_node: Parameter node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            Parameter information or None
        """
        if param_node.type == 'identifier':
            # Simple parameter (e.g., x)
            name = ast_handler.get_node_text(param_node, code_bytes)
            return {'name': name, 'type': None}
            
        elif param_node.type == 'typed_parameter':
            # Parameter with type annotation (e.g., x: int)
            name_node = param_node.child_by_field_name('name')
            type_node = param_node.child_by_field_name('type')
            
            if name_node:
                name = ast_handler.get_node_text(name_node, code_bytes)
                param_dict = {'name': name, 'type': None}
                
                if type_node:
                    param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                
                return param_dict
            
        elif param_node.type == 'default_parameter':
            # Parameter with default value (e.g., x=10)
            name_node = param_node.child_by_field_name('name')
            value_node = param_node.child_by_field_name('value')
            
            if name_node:
                name = ast_handler.get_node_text(name_node, code_bytes)
                param_dict = {'name': name, 'type': None, 'optional': True}
                
                if value_node:
                    param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                
                return param_dict
            
        elif param_node.type == 'typed_default_parameter':
            # Parameter with type and default value (e.g., x: int = 10)
            name_node = param_node.child_by_field_name('name')
            type_node = param_node.child_by_field_name('type')
            value_node = param_node.child_by_field_name('value')
            
            if name_node:
                name = ast_handler.get_node_text(name_node, code_bytes)
                param_dict = {'name': name, 'type': None, 'optional': True}
                
                if type_node:
                    param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                
                if value_node:
                    param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                
                return param_dict
                
        return None

    def _extract_properties(self, class_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract properties from a class node.
        
        Args:
            class_node: Class node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of property dictionaries
        """
        properties = []
        
        # These are usually identified by @property decorators
        # Handled by the _extract_methods method since they are methods with decorators
        
        # Add logic for instance properties assigned in __init__
        body_node = class_node.child_by_field_name('body')
        if not body_node:
            return properties
        
        # Find __init__ method
        init_query = "(function_definition name: (identifier) @method_name (#eq? @method_name \"__init__\")) @init_def"
        init_results = ast_handler.execute_query(init_query, body_node, code_bytes)
        
        init_node = None
        for (node, node_type) in init_results:
            if node_type == 'init_def':
                init_node = node
                break
        
        if init_node:
            # Find self.x = y assignments in __init__
            property_query = "(assignment left: (attribute object: (identifier) @obj attribute: (identifier) @prop_name)) @prop_assign"
            property_results = ast_handler.execute_query(property_query, init_node, code_bytes)
            
            for (node, node_type) in property_results:
                if node_type == 'obj':
                    obj_name = ast_handler.get_node_text(node, code_bytes)
                    if obj_name == 'self':
                        # This is a self.x = y assignment
                        prop_assign_node = ast_handler.find_parent_of_type(node, 'assignment')
                        if prop_assign_node:
                            left_node = prop_assign_node.child_by_field_name('left')
                            right_node = prop_assign_node.child_by_field_name('right')
                            
                            if left_node and left_node.type == 'attribute':
                                prop_name_node = left_node.child_by_field_name('attribute')
                                if prop_name_node:
                                    prop_name = ast_handler.get_node_text(prop_name_node, code_bytes)
                                    
                                    value_type = None
                                    value = None
                                    if right_node:
                                        value = ast_handler.get_node_text(right_node, code_bytes)
                                        
                                        # Try to infer type from value
                                        if value.isdigit():
                                            value_type = 'int'
                                        elif value.replace('.', '', 1).isdigit():
                                            value_type = 'float'
                                        elif value in ['True', 'False']:
                                            value_type = 'bool'
                                        elif value.startswith('"') or value.startswith("'"):
                                            value_type = 'str'
                                        elif value.startswith('['):
                                            value_type = 'list'
                                        elif value.startswith('{'):
                                            value_type = 'dict' if ':' in value else 'set'
                                    
                                    properties.append({
                                        'type': 'property',
                                        'name': prop_name,
                                        'content': f'self.{prop_name} = {value}' if value else f'self.{prop_name}',
                                        'range': {
                                            'start': {'line': prop_assign_node.start_point[0], 'column': prop_assign_node.start_point[1]},
                                            'end': {'line': prop_assign_node.end_point[0], 'column': prop_assign_node.end_point[1]}
                                        },
                                        'value': value,
                                        'value_type': value_type
                                    })
        
        return properties

    def _extract_static_properties(self, class_node, code_bytes, ast_handler, class_name) -> List[Dict]:
        """
        Extract static properties (class variables) from a class node.
        
        Args:
            class_node: Class node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            class_name: Name of the class
            
        Returns:
            List of static property dictionaries
        """
        static_properties = []
        
        body_node = class_node.child_by_field_name('body')
        if not body_node:
            return static_properties
        
        # Look for assignments directly in the class body (not in methods)
        # These are class variables
        assignment_query = "(expression_statement (assignment left: (identifier) @prop_name)) @prop_assign"
        assignment_results = ast_handler.execute_query(assignment_query, body_node, code_bytes)
        
        for (node, node_type) in assignment_results:
            if node_type == 'prop_name':
                prop_name = ast_handler.get_node_text(node, code_bytes)
                
                # Skip private or protected attributes that don't belong to this class
                if prop_name.startswith('__') or (prop_name.startswith('_') and not prop_name.startswith(f'_{class_name.lower()}')):
                    continue
                
                assign_node = ast_handler.find_parent_of_type(node, 'assignment')
                if assign_node:
                    expr_node = ast_handler.find_parent_of_type(assign_node, 'expression_statement')
                    if expr_node:
                        right_node = assign_node.child_by_field_name('right')
                        
                        value = None
                        value_type = None
                        if right_node:
                            value = ast_handler.get_node_text(right_node, code_bytes)
                            
                            # Try to infer type from value
                            if value.isdigit():
                                value_type = 'int'
                            elif value.replace('.', '', 1).isdigit():
                                value_type = 'float'
                            elif value in ['True', 'False']:
                                value_type = 'bool'
                            elif value.startswith('"') or value.startswith("'"):
                                value_type = 'str'
                            elif value.startswith('['):
                                value_type = 'list'
                            elif value.startswith('{'):
                                value_type = 'dict' if ':' in value else 'set'
                        
                        static_properties.append({
                            'type': 'static_property',
                            'name': prop_name,
                            'content': ast_handler.get_node_text(expr_node, code_bytes),
                            'range': {
                                'start': {'line': expr_node.start_point[0], 'column': expr_node.start_point[1]},
                                'end': {'line': expr_node.end_point[0], 'column': expr_node.end_point[1]}
                            },
                            'value': value,
                            'value_type': value_type,
                            'is_static': True
                        })
        
        return static_properties

    def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extract classes using regex."""
        try:
            pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code, re.DOTALL)
            classes = []
            for match in matches:
                name = match.group(1)
                content = match.group(0)
                start_pos = match.start()
                end_pos = match.end()
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
                
                # Extract class decorators
                decorators = []
                lines = code[:start_pos].splitlines()
                if lines:
                    indent = len(content) - len(content.lstrip())
                    i = len(lines) - 1
                    while i >= 0:
                        line = lines[i].strip()
                        if line.startswith('@'):
                            decorators.insert(0, {
                                'name': line[1:].split('(')[0] if '(' in line else line[1:],
                                'content': line
                            })
                        elif line and not line.startswith('#'):
                            break
                        i -= 1
                
                # For the regex case, we'll rely on subsequent extraction for members
                # The methods, properties will be extracted later when processing the class
                classes.append({
                    'type': 'class', 
                    'name': name, 
                    'content': content, 
                    'range': {
                        'start': {'line': lines_before, 'column': start_column}, 
                        'end': {'line': lines_total, 'column': end_column}
                    },
                    'decorators': decorators,
                    'members': {
                        'methods': [],
                        'properties': [],
                        'static_properties': []
                    }
                })
            return classes
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []