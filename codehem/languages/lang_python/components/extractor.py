"""
Python-specific element extractor implementation.
This module provides Python-specific implementation of the IElementExtractor interface.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from tree_sitter import Node

from codehem.core.components.base_implementations import BaseElementExtractor
from codehem.models.enums import CodeElementType
from codehem.models.code_element import CodeElement, CodeElementsResult
from codehem.models.range import CodeRange

logger = logging.getLogger(__name__)

class PythonElementExtractor(BaseElementExtractor):
    """
    Python-specific implementation of the element extractor.
    
    Extracts code elements from Python syntax trees.
    """
    
    def __init__(self, navigator):
        """
        Initialize the Python element extractor.
        
        Args:
            navigator: The syntax tree navigator to use
        """
        super().__init__('python', navigator)
    
    def extract_functions(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """
        Extract functions from a Python syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of function data dictionaries
        """
        logger.debug('Extracting Python functions')
        
        functions = []
        query_string = '(function_definition name: (identifier) @function_name) @function_def'
        
        try:
            matches = self.navigator.execute_query(tree, code_bytes, query_string)
            
            for node, capture_name in matches:
                if capture_name == 'function_def':
                    # Skip functions inside classes (methods)
                    parent_class = self.navigator.find_parent_of_type(node, 'class_definition')
                    if parent_class:
                        continue
                    
                    # Get function name
                    name_node = self.navigator.find_child_by_field_name(node, 'name')
                    if not name_node:
                        continue
                    
                    function_name = self.navigator.get_node_text(name_node, code_bytes)
                    function_content = self.navigator.get_node_text(node, code_bytes)
                    
                    # Get parameters
                    parameters_node = self.navigator.find_child_by_field_name(node, 'parameters')
                    parameters = self._extract_parameters(parameters_node, code_bytes) if parameters_node else []
                    
                    # Get return info
                    return_info = self._extract_return_info(node, code_bytes)
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create function info
                    function_info = {
                        'type': CodeElementType.FUNCTION.value,
                        'name': function_name,
                        'content': function_content,
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parameters': parameters,
                        'return_info': return_info,
                        'node': node
                    }
                    
                    functions.append(function_info)
            
            logger.debug(f'Extracted {len(functions)} Python functions')
        except Exception as e:
            logger.error(f'Error extracting Python functions: {e}', exc_info=True)
        
        return functions
    
    def extract_classes(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """
        Extract classes from a Python syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of class data dictionaries
        """
        logger.debug('Extracting Python classes')
        
        classes = []
        query_string = '(class_definition name: (identifier) @class_name) @class_def'
        
        try:
            matches = self.navigator.execute_query(tree, code_bytes, query_string)
            
            for node, capture_name in matches:
                if capture_name == 'class_def':
                    # Get class name
                    name_node = self.navigator.find_child_by_field_name(node, 'name')
                    if not name_node:
                        continue
                    
                    class_name = self.navigator.get_node_text(name_node, code_bytes)
                    class_content = self.navigator.get_node_text(node, code_bytes)
                    
                    # Get inheritance
                    inheritance = []
                    bases_node = self.navigator.find_child_by_field_name(node, 'superclasses')
                    if bases_node:
                        for i in range(bases_node.named_child_count):
                            base_node = bases_node.named_child(i)
                            inheritance.append(self.navigator.get_node_text(base_node, code_bytes))
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create class info
                    class_info = {
                        'type': CodeElementType.CLASS.value,
                        'name': class_name,
                        'content': class_content,
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'additional_data': {
                            'inheritance': inheritance
                        },
                        'node': node
                    }
                    
                    classes.append(class_info)
            
            logger.debug(f'Extracted {len(classes)} Python classes')
        except Exception as e:
            logger.error(f'Error extracting Python classes: {e}', exc_info=True)
        
        return classes
    
    def extract_methods(self, tree: Node, code_bytes: bytes, 
                      class_name: Optional[str]=None) -> List[Dict]:
        """
        Extract methods from a Python syntax tree, optionally filtering by class.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            class_name: Optional class name to filter by
            
        Returns:
            List of method data dictionaries
        """
        logger.debug(f'Extracting Python methods' + (f' for class {class_name}' if class_name else ''))
        
        methods = []
        
        # Build query based on whether we're filtering by class
        if class_name:
            query_string = f'''
            (class_definition
                name: (identifier) @class_name (#eq? @class_name "{class_name}")
                body: (block (function_definition) @method_def)
            )
            (class_definition
                name: (identifier) @class_name (#eq? @class_name "{class_name}")
                body: (block (decorated_definition (function_definition) @method_def))
            )
            '''
        else:
            query_string = '''
            (class_definition
                name: (identifier) @class_name
                body: (block (function_definition) @method_def)
            )
            (class_definition
                name: (identifier) @class_name
                body: (block (decorated_definition (function_definition) @method_def))
            )
            '''
        
        try:
            matches = self.navigator.execute_query(tree, code_bytes, query_string)
            
            processed_nodes = set()
            for node, capture_name in matches:
                if capture_name == 'method_def' and node.id not in processed_nodes:
                    processed_nodes.add(node.id)
                    
                    # Get method name
                    name_node = self.navigator.find_child_by_field_name(node, 'name')
                    if not name_node:
                        continue
                    
                    method_name = self.navigator.get_node_text(name_node, code_bytes)
                    method_content = self.navigator.get_node_text(node, code_bytes)
                    
                    # Get parent class name
                    parent_class_node = self.navigator.find_parent_of_type(node, 'class_definition')
                    parent_name = None
                    if parent_class_node:
                        parent_name_node = self.navigator.find_child_by_field_name(parent_class_node, 'name')
                        if parent_name_node:
                            parent_name = self.navigator.get_node_text(parent_name_node, code_bytes)
                    
                    # Skip if we're filtering by class and this doesn't match
                    if class_name and parent_name != class_name:
                        continue
                    
                    # Get parameters
                    parameters_node = self.navigator.find_child_by_field_name(node, 'parameters')
                    parameters = self._extract_parameters(parameters_node, code_bytes, is_method=True) if parameters_node else []
                    
                    # Get return info
                    return_info = self._extract_return_info(node, code_bytes)
                    
                    # Check if this is a property decorator
                    is_property = False
                    is_setter = False
                    decorated_def = self.navigator.find_parent_of_type(node, 'decorated_definition')
                    if decorated_def:
                        for child in decorated_def.children:
                            if child.type == 'decorator':
                                decorator_text = self.navigator.get_node_text(child, code_bytes)
                                if decorator_text.strip() == '@property':
                                    is_property = True
                                elif '.setter' in decorator_text:
                                    is_setter = True
                    
                    # Determine element type
                    element_type = CodeElementType.METHOD.value
                    if is_property:
                        element_type = CodeElementType.PROPERTY_GETTER.value
                    elif is_setter:
                        element_type = CodeElementType.PROPERTY_SETTER.value
                    
                    # Get range - use decorated_def if available for better range
                    range_node = decorated_def if decorated_def else node
                    start_line, end_line = self.navigator.get_node_range(range_node)
                    
                    # Create method info
                    method_info = {
                        'type': element_type,
                        'name': method_name,
                        'content': self.navigator.get_node_text(range_node, code_bytes),
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parent_name': parent_name,
                        'parameters': parameters,
                        'return_info': return_info,
                        'node': node,
                        'range_node': range_node
                    }
                    
                    methods.append(method_info)
            
            logger.debug(f'Extracted {len(methods)} Python methods')
        except Exception as e:
            logger.error(f'Error extracting Python methods: {e}', exc_info=True)
        
        return methods
    
    def extract_properties(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """
        Extract properties from a Python syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of property data dictionaries
        """
        logger.debug('Extracting Python properties')
        
        properties = []
        
        # Property getters (using @property decorator)
        getter_query = '''
        (decorated_definition
            (decorator
                (identifier) @decorator_name (#eq? @decorator_name "property")
            )
            (function_definition
                name: (identifier) @property_name
            )
        ) @property_def
        '''
        
        # Property setters (using @x.setter decorator)
        setter_query = '''
        (decorated_definition
            (decorator
                (attribute
                    attribute: (identifier) @setter_attr (#eq? @setter_attr "setter")
                )
            )
            (function_definition
                name: (identifier) @property_name
            )
        ) @setter_def
        '''
        
        try:
            # Extract property getters
            getter_matches = self.navigator.execute_query(tree, code_bytes, getter_query)
            for node, capture_name in getter_matches:
                if capture_name == 'property_def':
                    function_node = None
                    for child in node.children:
                        if child.type == 'function_definition':
                            function_node = child
                            break
                    
                    if not function_node:
                        continue
                    
                    # Get property name
                    name_node = self.navigator.find_child_by_field_name(function_node, 'name')
                    if not name_node:
                        continue
                    
                    property_name = self.navigator.get_node_text(name_node, code_bytes)
                    
                    # Get parent class
                    parent_class_node = self.navigator.find_parent_of_type(node, 'class_definition')
                    parent_name = None
                    if parent_class_node:
                        parent_name_node = self.navigator.find_child_by_field_name(parent_class_node, 'name')
                        if parent_name_node:
                            parent_name = self.navigator.get_node_text(parent_name_node, code_bytes)
                    
                    # Get return info for type hint
                    return_info = self._extract_return_info(function_node, code_bytes)
                    value_type = return_info.get('return_type')
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create property info
                    property_info = {
                        'type': CodeElementType.PROPERTY_GETTER.value,
                        'name': property_name,
                        'content': self.navigator.get_node_text(node, code_bytes),
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parent_name': parent_name,
                        'value_type': value_type,
                        'node': node
                    }
                    
                    properties.append(property_info)
            
            # Extract property setters
            setter_matches = self.navigator.execute_query(tree, code_bytes, setter_query)
            for node, capture_name in setter_matches:
                if capture_name == 'setter_def':
                    function_node = None
                    for child in node.children:
                        if child.type == 'function_definition':
                            function_node = child
                            break
                    
                    if not function_node:
                        continue
                    
                    # Get property name
                    name_node = self.navigator.find_child_by_field_name(function_node, 'name')
                    if not name_node:
                        continue
                    
                    property_name = self.navigator.get_node_text(name_node, code_bytes)
                    
                    # Get parent class
                    parent_class_node = self.navigator.find_parent_of_type(node, 'class_definition')
                    parent_name = None
                    if parent_class_node:
                        parent_name_node = self.navigator.find_child_by_field_name(parent_class_node, 'name')
                        if parent_name_node:
                            parent_name = self.navigator.get_node_text(parent_name_node, code_bytes)
                    
                    # Get value type from parameter
                    parameters_node = self.navigator.find_child_by_field_name(function_node, 'parameters')
                    params = self._extract_parameters(parameters_node, code_bytes, is_method=True) if parameters_node else []
                    
                    value_type = None
                    if len(params) > 1:  # Skip 'self'
                        value_param = params[1]
                        value_type = value_param.get('type')
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create property info
                    property_info = {
                        'type': CodeElementType.PROPERTY_SETTER.value,
                        'name': property_name,
                        'content': self.navigator.get_node_text(node, code_bytes),
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parent_name': parent_name,
                        'value_type': value_type,
                        'node': node
                    }
                    
                    properties.append(property_info)
            
            logger.debug(f'Extracted {len(properties)} Python properties')
        except Exception as e:
            logger.error(f'Error extracting Python properties: {e}', exc_info=True)
        
        # Also extract instance attributes set in __init__ (e.g., self.foo = value)
        try:
            instance_props = self._extract_instance_attributes(tree, code_bytes)
            properties.extend(instance_props)
        except Exception as e:
            logger.error(f'Error extracting Python instance attributes: {e}', exc_info=True)

        return properties

    def _extract_instance_attributes(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """Extract instance attributes assigned in __init__ methods within classes."""
        instance_props: List[Dict] = []

        # Query all classes with their __init__ definitions
        init_query = r'''
        (class_definition
            name: (identifier) @class_name
            body: (block
                (function_definition
                    name: (identifier) @method_name (#eq? @method_name "__init__")
                    body: (block) @init_block
                )
            )
        ) @class_def
        '''

        matches = self.navigator.execute_query(tree, code_bytes, init_query)

        # Build a list of (class_name, init_block_node) pairs
        init_blocks: List[Tuple[str, Node]] = []
        for node, capture in matches:
            if capture == 'init_block':
                # Find the class name for this block by walking up
                class_node = self.navigator.find_parent_of_type(node, 'class_definition')
                class_name = None
                if class_node:
                    name_node = self.navigator.find_child_by_field_name(class_node, 'name')
                    if name_node:
                        class_name = self.navigator.get_node_text(name_node, code_bytes)
                if class_name:
                    init_blocks.append((class_name, node))

        seen: set[tuple[str, str, int]] = set()
        for class_name, init_block in init_blocks:
            # Iterate over statements inside the init block
            for i in range(init_block.named_child_count):
                stmt = init_block.named_child(i)
                node_for_range = stmt
                target_assignment = None

                # Many assignments are wrapped in expression_statement
                inner = stmt.named_child(0) if stmt.type == 'expression_statement' and stmt.named_child_count > 0 else None
                if inner and inner.type in ('assignment', 'typed_assignment'):
                    target_assignment = inner
                elif stmt.type in ('assignment', 'typed_assignment'):
                    target_assignment = stmt

                if not target_assignment:
                    continue

                left = target_assignment.child_by_field_name('left')
                if left is None:
                    continue
                # We only care about attributes on self: self.attr
                if left.type == 'attribute':
                    obj_node = left.child_by_field_name('object')
                    attr_node = left.child_by_field_name('attribute')
                    if not obj_node or not attr_node:
                        continue
                    obj_text = self.navigator.get_node_text(obj_node, code_bytes)
                    if obj_text != 'self':
                        continue
                    prop_name = self.navigator.get_node_text(attr_node, code_bytes)
                else:
                    continue

                # Determine type hint if present (typed_assignment or type field)
                type_node = target_assignment.child_by_field_name('type')
                value_type = self.navigator.get_node_text(type_node, code_bytes) if type_node else None

                # Build property info
                start_line, end_line = self.navigator.get_node_range(node_for_range)
                key = (class_name, prop_name, start_line)
                if key in seen:
                    continue
                seen.add(key)

                prop_info = {
                    'type': CodeElementType.PROPERTY.value,
                    'name': prop_name,
                    'content': self.navigator.get_node_text(node_for_range, code_bytes),
                    'range': {
                        'start': {'line': start_line, 'column': 0},
                        'end': {'line': end_line, 'column': 0}
                    },
                    'parent_name': class_name,
                    'value_type': value_type,
                    'node': node_for_range
                }
                instance_props.append(prop_info)

        logger.debug(f'Extracted {len(instance_props)} Python instance attributes')
        return instance_props
    
    def extract_static_properties(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """
        Extract static properties from a Python syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of static property data dictionaries
        """
        logger.debug('Extracting Python static properties')
        
        static_props = []
        
        # Class-level assignments
        query_string = '''
        (class_definition
            name: (identifier) @class_name
            body: (block
                (expression_statement
                    (assignment
                        left: (identifier) @property_name
                        right: (_) @property_value
                    )
                ) @assignment_stmt
            )
        )
        '''
        
        # Typed class-level assignments (Python 3.6+)
        typed_query = '''
        (class_definition
            name: (identifier) @class_name
            body: (block
                (expression_statement
                    (assignment
                        left: (identifier) @property_name
                        type: (type) @property_type
                        right: (_) @property_value
                    )
                ) @typed_assignment_stmt
            )
        )
        '''
        
        try:
            # Extract regular static properties
            matches = self.navigator.execute_query(tree, code_bytes, query_string)
            for node, capture_name in matches:
                if capture_name == 'assignment_stmt':
                    class_node = self.navigator.find_parent_of_type(node, 'class_definition')
                    if not class_node:
                        continue
                    
                    assignment_node = None
                    for child in node.children:
                        if child.type == 'assignment':
                            assignment_node = child
                            break
                    
                    if not assignment_node:
                        continue
                    
                    # Get property name
                    name_node = self.navigator.find_child_by_field_name(assignment_node, 'left')
                    if not name_node or name_node.type != 'identifier':
                        continue
                    
                    property_name = self.navigator.get_node_text(name_node, code_bytes)
                    
                    # Skip if starts with _ (pseudo-private)
                    if property_name.startswith('_'):
                        continue
                    
                    # Get property value
                    value_node = self.navigator.find_child_by_field_name(assignment_node, 'right')
                    property_value = self.navigator.get_node_text(value_node, code_bytes) if value_node else None
                    
                    # Get parent class name
                    class_name_node = self.navigator.find_child_by_field_name(class_node, 'name')
                    class_name = self.navigator.get_node_text(class_name_node, code_bytes) if class_name_node else None
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Infer type from value
                    value_type = self._infer_type_from_value(property_value) if property_value else None
                    
                    # Create static property info
                    prop_info = {
                        'type': CodeElementType.STATIC_PROPERTY.value,
                        'name': property_name,
                        'content': self.navigator.get_node_text(node, code_bytes),
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parent_name': class_name,
                        'value_type': value_type,
                        'additional_data': {'value': property_value},
                        'node': node
                    }
                    
                    static_props.append(prop_info)
            
            # Extract typed static properties
            typed_matches = self.navigator.execute_query(tree, code_bytes, typed_query)
            for node, capture_name in typed_matches:
                if capture_name == 'typed_assignment_stmt':
                    class_node = self.navigator.find_parent_of_type(node, 'class_definition')
                    if not class_node:
                        continue
                    
                    assignment_node = None
                    for child in node.children:
                        if child.type == 'assignment':
                            assignment_node = child
                            break

                    if not assignment_node:
                        continue

                    # Get property name and type
                    name_node = self.navigator.find_child_by_field_name(assignment_node, 'left')
                    type_node = self.navigator.find_child_by_field_name(assignment_node, 'type')
                    
                    if not name_node:
                        continue
                    
                    property_name = self.navigator.get_node_text(name_node, code_bytes)
                    
                    # Skip if starts with _ (pseudo-private)
                    if property_name.startswith('_'):
                        continue
                    
                    # Get property type and value
                    property_type = self.navigator.get_node_text(type_node, code_bytes) if type_node else None
                    
                    value_node = self.navigator.find_child_by_field_name(assignment_node, 'right')
                    property_value = self.navigator.get_node_text(value_node, code_bytes) if value_node else None
                    
                    # Get parent class name
                    class_name_node = self.navigator.find_child_by_field_name(class_node, 'name')
                    class_name = self.navigator.get_node_text(class_name_node, code_bytes) if class_name_node else None
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create static property info
                    prop_info = {
                        'type': CodeElementType.STATIC_PROPERTY.value,
                        'name': property_name,
                        'content': self.navigator.get_node_text(node, code_bytes),
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parent_name': class_name,
                        'value_type': property_type,
                        'additional_data': {'value': property_value},
                        'node': node
                    }
                    
                    static_props.append(prop_info)
            
            logger.debug(f'Extracted {len(static_props)} Python static properties')
        except Exception as e:
            logger.error(f'Error extracting Python static properties: {e}', exc_info=True)
        
        return static_props
    
    def extract_imports(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """
        Extract imports from a Python syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of import data dictionaries
        """
        logger.debug('Extracting Python imports')
        
        imports = []
        
        # Regular imports
        import_query = '(import_statement) @import_stmt'
        
        # From imports
        from_query = '(import_from_statement) @from_stmt'
        
        try:
            # Process regular imports
            import_matches = self.navigator.execute_query(tree, code_bytes, import_query)
            for node, capture_name in import_matches:
                if capture_name == 'import_stmt':
                    content = self.navigator.get_node_text(node, code_bytes)
                    
                    # Get module names
                    modules = []
                    names_node = self.navigator.find_child_by_field_name(node, 'name')
                    if names_node:
                        for i in range(names_node.named_child_count):
                            module_node = names_node.named_child(i)
                            modules.append(self.navigator.get_node_text(module_node, code_bytes))
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create import info
                    import_info = {
                        'type': CodeElementType.IMPORT.value,
                        'name': ', '.join(modules) if modules else 'import',
                        'content': content,
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'additional_data': {'modules': modules},
                        'node': node
                    }
                    
                    imports.append(import_info)
            
            # Process from imports
            from_matches = self.navigator.execute_query(tree, code_bytes, from_query)
            for node, capture_name in from_matches:
                if capture_name == 'from_stmt':
                    content = self.navigator.get_node_text(node, code_bytes)
                    
                    # Get module name
                    module_node = self.navigator.find_child_by_field_name(node, 'module')
                    module_name = self.navigator.get_node_text(module_node, code_bytes) if module_node else None
                    
                    # Get imported names
                    names = []
                    names_node = self.navigator.find_child_by_field_name(node, 'name')
                    if names_node:
                        for i in range(names_node.named_child_count):
                            name_node = names_node.named_child(i)
                            names.append(self.navigator.get_node_text(name_node, code_bytes))
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create import info
                    import_info = {
                        'type': CodeElementType.IMPORT.value,
                        'name': module_name or 'from_import',
                        'content': content,
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'additional_data': {
                            'module': module_name,
                            'names': names
                        },
                        'node': node
                    }
                    
                    imports.append(import_info)
            
            logger.debug(f'Extracted {len(imports)} Python imports')
        except Exception as e:
            logger.error(f'Error extracting Python imports: {e}', exc_info=True)
        
        return imports
    
    def extract_decorators(self, tree: Node, code_bytes: bytes) -> List[Dict]:
        """
        Extract decorators from a Python syntax tree.
        
        Args:
            tree: The syntax tree to extract from
            code_bytes: The original code as bytes
            
        Returns:
            List of decorator data dictionaries
        """
        logger.debug('Extracting Python decorators')
        
        decorators = []
        query_string = '(decorator) @decorator_node'
        
        try:
            matches = self.navigator.execute_query(tree, code_bytes, query_string)
            
            for node, capture_name in matches:
                if capture_name == 'decorator_node':
                    content = self.navigator.get_node_text(node, code_bytes)
                    
                    # Get decorator name
                    name = None
                    if node.child_count > 1:
                        name_node = node.child(1)  # Skip @ symbol
                        name = self.navigator.get_node_text(name_node, code_bytes)
                    
                    if not name:
                        name = content.lstrip('@').split('(')[0].strip()
                    
                    # Get parent element being decorated
                    parent_def = self.navigator.find_parent_of_type(node, 'decorated_definition')
                    if not parent_def:
                        continue
                    
                    decorated_element = None
                    for child in parent_def.children:
                        if child.type in ['function_definition', 'class_definition']:
                            decorated_element = child
                            break
                    
                    if not decorated_element:
                        continue
                    
                    # Get parent class if this is decorating a method
                    parent_name = None
                    if decorated_element.type == 'function_definition':
                        parent_class = self.navigator.find_parent_of_type(parent_def, 'class_definition')
                        if parent_class:
                            parent_name_node = self.navigator.find_child_by_field_name(parent_class, 'name')
                            if parent_name_node:
                                parent_name = self.navigator.get_node_text(parent_name_node, code_bytes)
                    
                    # Get decorated element name
                    decorated_name = None
                    decorated_name_node = self.navigator.find_child_by_field_name(decorated_element, 'name')
                    if decorated_name_node:
                        decorated_name = self.navigator.get_node_text(decorated_name_node, code_bytes)
                    
                    if parent_name and decorated_name:
                        decorated_name = f"{parent_name}.{decorated_name}"
                    
                    # Get range
                    start_line, end_line = self.navigator.get_node_range(node)
                    
                    # Create decorator info
                    decorator_info = {
                        'type': CodeElementType.DECORATOR.value,
                        'name': name,
                        'content': content,
                        'range': {
                            'start': {'line': start_line, 'column': 0},
                            'end': {'line': end_line, 'column': 0}
                        },
                        'parent_name': decorated_name,
                        'node': node
                    }
                    
                    decorators.append(decorator_info)
            
            logger.debug(f'Extracted {len(decorators)} Python decorators')
        except Exception as e:
            logger.error(f'Error extracting Python decorators: {e}', exc_info=True)
        
        return decorators
    
    def _extract_parameters(self, node: Node, code_bytes: bytes, is_method: bool = False) -> List[Dict]:
        """Extract parameters from a parameter list node."""
        parameters = []
        
        if not node:
            return parameters
        
        # Skip first parameter (self) for methods if requested
        start_idx = 1 if is_method else 0
        
        for i in range(start_idx, node.named_child_count):
            param_node = node.named_child(i)
            param_info = {'name': None, 'type': None, 'default': None}
            
            # Handle different parameter node types
            if param_node.type == 'identifier':
                # Simple parameter (no type, no default)
                param_info['name'] = self.navigator.get_node_text(param_node, code_bytes)
            
            elif param_node.type == 'typed_parameter':
                # Parameter with type annotation
                name_node = self.navigator.find_child_by_field_name(param_node, 'name')
                type_node = self.navigator.find_child_by_field_name(param_node, 'type')
                
                if name_node:
                    param_info['name'] = self.navigator.get_node_text(name_node, code_bytes)
                
                if type_node:
                    param_info['type'] = self.navigator.get_node_text(type_node, code_bytes)
            
            elif param_node.type == 'default_parameter':
                # Parameter with default value
                name_node = self.navigator.find_child_by_field_name(param_node, 'name')
                value_node = self.navigator.find_child_by_field_name(param_node, 'value')
                
                if name_node:
                    if name_node.type == 'identifier':
                        param_info['name'] = self.navigator.get_node_text(name_node, code_bytes)
                    elif name_node.type == 'typed_parameter':
                        inner_name = self.navigator.find_child_by_field_name(name_node, 'name')
                        inner_type = self.navigator.find_child_by_field_name(name_node, 'type')
                        
                        if inner_name:
                            param_info['name'] = self.navigator.get_node_text(inner_name, code_bytes)
                        
                        if inner_type:
                            param_info['type'] = self.navigator.get_node_text(inner_type, code_bytes)
                
                if value_node:
                    param_info['default'] = self.navigator.get_node_text(value_node, code_bytes)
            
            # Add parameter if we have a name
            if param_info['name']:
                parameters.append(param_info)
        
        return parameters
    
    def _extract_return_info(self, node: Node, code_bytes: bytes) -> Dict:
        """Extract return type and values from a function node."""
        return_info = {'return_type': None, 'return_values': []}
        
        if not node:
            return return_info
        
        # Get return type annotation if present
        return_type = None
        return_node = self.navigator.find_child_by_field_name(node, 'return_type')
        if return_node:
            return_type = self.navigator.get_node_text(return_node, code_bytes)
        
        return_info['return_type'] = return_type
        
        # Find return statements in function body
        body_node = self.navigator.find_child_by_field_name(node, 'body')
        if body_node:
            return_query = '(return_statement) @return_stmt'
            try:
                matches = self.navigator.execute_query(body_node, code_bytes, return_query)
                for return_node, _ in matches:
                    value_node = return_node.child(1) if return_node.child_count > 1 else None
                    if value_node:
                        return_value = self.navigator.get_node_text(value_node, code_bytes)
                        if return_value not in return_info['return_values']:
                            return_info['return_values'].append(return_value)
            except Exception as e:
                logger.debug(f'Error extracting return values: {e}')
        
        return return_info
    
    def _infer_type_from_value(self, value: str) -> Optional[str]:
        """Infer the type of a value from its string representation."""
        if not value:
            return None
        
        value = value.strip()
        
        if value.isdigit():
            return 'int'
        elif value.replace('.', '', 1).isdigit():
            return 'float'
        elif value in ['True', 'False']:
            return 'bool'
        elif value in ['None']:
            return 'None'
        elif (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return 'str'
        elif value.startswith('[') and value.endswith(']'):
            return 'list'
        elif value.startswith('(') and value.endswith(')'):
            return 'tuple'
        elif value.startswith('{') and value.endswith('}'):
            if ':' in value:
                return 'dict'
            else:
                return 'set'
        
        return None
