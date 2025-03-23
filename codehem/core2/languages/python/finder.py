"""
Python-specific analyzer implementation.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from tree_sitter import Node
from ...engine.base_language_finder import BaseLanguageFinder
from ...engine.ast_handler import ASTHandler
from ...models import CodeElementType
from .template import TEMPLATES, ADDITIONAL_QUERIES
logger = logging.getLogger(__name__)

class PythonFinder(BaseLanguageFinder):
    """
    Python-specific implementation of the code analyzer.
    Combines the capabilities of the former Finder and Strategy classes.
    """

    def __init__(self, ast_handler: ASTHandler):
        """
        Initialize the Python analyzer.

        Args:
            ast_handler: AST handler for Python
        """
        self.ast_handler = ast_handler
        self.templates = TEMPLATES
        self.additional_queries = ADDITIONAL_QUERIES

    @property
    def language_code(self) -> str:
        """Get the language code."""
        return 'python'

    @property
    def file_extensions(self) -> List[str]:
        """Get file extensions supported by this language."""
        return ['.py']

    @property
    def supported_element_types(self) -> List[str]:
        """Get element types supported by this language."""
        return [CodeElementType.CLASS.value, CodeElementType.METHOD.value, CodeElementType.FUNCTION.value, CodeElementType.PROPERTY.value, CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value, CodeElementType.STATIC_PROPERTY.value, CodeElementType.IMPORT.value, CodeElementType.MODULE.value]

    def can_handle(self, code: str) -> bool:
        """
        Check if this analyzer can handle the given code.
        
        Args:
            code: Source code as string
            
        Returns:
            True if this analyzer can handle the code, False otherwise
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(code)
            indicators = self.additional_queries['language_indicators']
            class_count = len(self._execute_query(root, code_bytes, indicators['python_class']))
            function_count = len(self._execute_query(root, code_bytes, indicators['python_function']))
            import_count = len(self._execute_query(root, code_bytes, indicators['python_import']))
            import_from_count = len(self._execute_query(root, code_bytes, indicators['python_import_from']))
            python_indicators = class_count + function_count + import_count + import_from_count
            var_declarations = len(self._execute_query(root, code_bytes, indicators['js_var_declarations']))
            function_with_braces = len(self._execute_query(root, code_bytes, indicators['js_function_braces']))
            if python_indicators > 0 and var_declarations == 0 and (function_with_braces == 0):
                return True
            if python_indicators == 0:
                python_patterns = [r'def\s+\w+\s*\([^)]*\)\s*:', r'class\s+\w+(\s*\([^)]*\))?\s*:', r'^@\w+', r'import\s+\w+', r'from\s+[\w.]+\s+import']
                for pattern in python_patterns:
                    if re.search(pattern, code, re.MULTILINE):
                        return True
            return False
        except Exception as e:
            logger.debug(f'Error in Python language detection: {str(e)}')
            return False

    def get_confidence_score(self, code: str) -> float:
        """
        Calculate a confidence score for how likely the code is Python.
        
        Args:
            code: Source code as string
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(code)
            indicators = self.additional_queries['language_indicators']
            class_count = len(self._execute_query(root, code_bytes, indicators['python_class']))
            function_count = len(self._execute_query(root, code_bytes, indicators['python_function']))
            import_count = len(self._execute_query(root, code_bytes, indicators['python_import']))
            import_from_count = len(self._execute_query(root, code_bytes, indicators['python_import_from']))
            decorator_count = len(self._execute_query(root, code_bytes, indicators['python_decorators']))
            python_indicators = class_count * 3 + function_count * 2 + import_count + import_from_count + decorator_count * 2
            var_declarations = len(self._execute_query(root, code_bytes, indicators['js_var_declarations']))
            function_with_braces = len(self._execute_query(root, code_bytes, indicators['js_function_braces']))
            arrow_functions = len(self._execute_query(root, code_bytes, indicators['js_arrow_functions']))
            negative_indicators = var_declarations * 2 + function_with_braces * 3 + arrow_functions * 3
            confidence = python_indicators - negative_indicators
            max_possible = 10
            return max(0.0, min(1.0, confidence / max_possible))
        except Exception as e:
            logger.debug(f'Error calculating Python confidence score: {str(e)}')
            python_patterns = {r'def\s+\w+\s*\([^)]*\)\s*:': 3, r'class\s+\w+(\s*\([^)]*\))?\s*:': 3, r'^@\w+': 2, r'import\s+\w+': 1, r'from\s+[\w.]+\s+import': 1, r'self\.': 2, r'#.*$': 1}
            negative_patterns = {r'function\s+\w+\s*\(': -3, r'var\s+\w+\s*=': -2, r'let\s+\w+\s*=': -2, r'const\s+\w+\s*=': -2, r'}\s*else\s*{': -2, r'interface\s+\w+\s*{': -3}
            confidence = 0
            for (pattern, weight) in python_patterns.items():
                if re.search(pattern, code, re.MULTILINE):
                    confidence += weight
            for (pattern, weight) in negative_patterns.items():
                if re.search(pattern, code, re.MULTILINE):
                    confidence += weight
            max_possible = sum([w for w in python_patterns.values() if w > 0])
            min_possible = sum([w for w in negative_patterns.values() if w < 0])
            normalized = (confidence - min_possible) / (max_possible - min_possible)
            return max(0.0, min(1.0, normalized))

    def detect_element_type(self, code: str) -> str:
        """
        Detect the type of element in the code.
        
        Args:
            code: Code to analyze
            
        Returns:
            Element type string
        """
        code = code.strip()
        if not code:
            return CodeElementType.MODULE.value
        try:
            (root, code_bytes) = self.ast_handler.parse(code)
            class_nodes = self._execute_query(root, code_bytes, '(class_definition) @class')
            if class_nodes:
                return CodeElementType.CLASS.value
            property_getter = self._execute_query(root, code_bytes, '(decorated_definition decorator: (decorator name: (identifier) @dec_name (#eq? @dec_name "property"))) @prop_getter')
            if property_getter:
                return CodeElementType.PROPERTY_GETTER.value
            property_setter = self._execute_query(root, code_bytes, '(decorated_definition decorator: (decorator name: (attribute object: (_) attribute: (identifier) @attr_name (#eq? @attr_name "setter")))) @prop_setter')
            if property_setter:
                return CodeElementType.PROPERTY_SETTER.value
            function_nodes = self._execute_query(root, code_bytes, '(function_definition) @function')
            if function_nodes:
                first_param = self._execute_query(root, code_bytes, '(function_definition parameters: (parameters (identifier) @first_param))')
                if first_param and self.ast_handler.get_node_text(first_param[0][0], code_bytes) == 'self':
                    return CodeElementType.METHOD.value
                else:
                    return CodeElementType.FUNCTION.value
            self_property = self._execute_query(root, code_bytes, '(assignment left: (attribute object: (identifier) @obj (#eq? @obj "self"))) @self_prop')
            if self_property:
                return CodeElementType.PROPERTY.value
            static_property = self._execute_query(root, code_bytes, '(assignment left: (identifier) @name) @static_prop')
            if static_property:
                return CodeElementType.STATIC_PROPERTY.value
            imports = self._execute_query(root, code_bytes, '(import_statement) @import (import_from_statement) @import_from')
            if imports:
                return CodeElementType.IMPORT.value
            return CodeElementType.MODULE.value
        except Exception as e:
            logger.debug(f'Error detecting element type: {str(e)}')
            if re.match(r'class\s+\w+(\s*\([^)]*\))?\s*:', code):
                return CodeElementType.CLASS.value
            if re.match(r'@property\s*\ndef\s+\w+\s*\(', code):
                return CodeElementType.PROPERTY_GETTER.value
            if re.match(r'@\w+\.setter\s*\ndef\s+\w+\s*\(', code):
                return CodeElementType.PROPERTY_SETTER.value
            if re.match(r'def\s+\w+\s*\(\s*self', code):
                return CodeElementType.METHOD.value
            if re.match(r'def\s+\w+\s*\(', code):
                return CodeElementType.FUNCTION.value
            if re.search(r'self\.\w+\s*=', code) and (not re.search(r'def\s+|class\s+|import\s+|from\s+', code)):
                return CodeElementType.PROPERTY.value
            if re.match(r'\w+\s*=', code) and (not re.search(r'def\s+|class\s+|import\s+|from\s+', code)):
                return CodeElementType.STATIC_PROPERTY.value
            if re.match(r'(import\s+|from\s+\w+\s+import)', code):
                return CodeElementType.IMPORT.value
            return CodeElementType.MODULE.value

    def find_element(self, code: str, element_type: str, name: str, parent_name: Optional[str]=None) -> Tuple[int, int]:
        """
        Find an element of the specified type in the code.
        
        Args:
            code: Source code as string
            element_type: Type of element to find
            name: Name of the element to find
            parent_name: Name of the parent element (e.g., class name for methods)
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        handler = self._get_element_handler(element_type)
        if handler:
            return handler(code, name, parent_name)
        if element_type not in self.templates:
            return (0, 0)
        template = self.templates[element_type]['find_one']
        param_name = f'{element_type.lower()}_name'
        template = template.format(**{param_name: name})
        return self._find_element_by_query(code, template)

    def find_by_xpath(self, code: str, xpath: str) -> Tuple[int, int]:
        """
        Find an element in the code using an XPath-like expression.
        
        Args:
            code: Source code as string
            xpath: XPath-like expression (e.g., 'ClassName.method_name')
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        return super().find_by_xpath(code, xpath)

    def _get_element_handler(self, element_type: str) -> Optional[callable]:
        """
        Get the handler function for the specified element type.
        
        Args:
            element_type: Element type
            
        Returns:
            Handler function or None if no specific handler
        """
        handlers = {CodeElementType.METHOD.value: self._handle_method, CodeElementType.PROPERTY.value: self._handle_property, CodeElementType.PROPERTY_GETTER.value: self._handle_property_getter, CodeElementType.PROPERTY_SETTER.value: self._handle_property_setter, CodeElementType.STATIC_PROPERTY.value: self._handle_static_property, CodeElementType.IMPORT.value: self._handle_import}
        return handlers.get(element_type)

    def _handle_method(self, code: str, name: str, parent_name: Optional[str]) -> Tuple[int, int]:
        """Handle finding a method."""
        if parent_name:
            return self.find_element_in_parent(code, CodeElementType.CLASS.value, parent_name, CodeElementType.METHOD.value, name)
        return self._find_element_by_query(code, self.templates[CodeElementType.METHOD.value]['find_one'].format(method_name=name))

    def _handle_property_getter(self, code: str, name: str, parent_name: Optional[str]) -> Tuple[int, int]:
        """Handle finding a property getter."""
        if parent_name:
            return self.find_element_in_parent(code, CodeElementType.CLASS.value, parent_name, CodeElementType.PROPERTY_GETTER.value, name, 'property_getter')
        return self._find_element_by_query(code, self.templates[CodeElementType.PROPERTY_GETTER.value]['find_one'].format(property_name=name))

    def _handle_property_setter(self, code: str, name: str, parent_name: Optional[str]) -> Tuple[int, int]:
        """Handle finding a property setter."""
        if parent_name:
            return self.find_element_in_parent(code, CodeElementType.CLASS.value, parent_name, CodeElementType.PROPERTY_SETTER.value, name, 'property_setter')
        return self._find_element_by_query(code, self.templates[CodeElementType.PROPERTY_SETTER.value]['find_one'].format(property_name=name))

    def _handle_static_property(self, code: str, name: str, parent_name: Optional[str]) -> Tuple[int, int]:
        """Handle finding a static property."""
        if parent_name:
            (root, code_bytes) = self.ast_handler.parse(code)
            class_query = self.templates[CodeElementType.CLASS.value]['find_one'].format(class_name=parent_name)
            class_nodes = self._execute_query(root, code_bytes, class_query)
            class_node = None
            for (node, capture_name) in class_nodes:
                if capture_name == 'class':
                    class_node = node
                    break
            if not class_node:
                return (0, 0)
            static_property_query = self.templates[CodeElementType.STATIC_PROPERTY.value]['find_one'].format(property_name=name)
            static_property_nodes = self._execute_query(class_node, code_bytes, static_property_query)
            for (node, capture_name) in static_property_nodes:
                if capture_name == 'prop_name':
                    assignment_node = self._find_parent_of_type(node, 'assignment')
                    if assignment_node:
                        expr_node = self._find_parent_of_type(assignment_node, 'expression_statement')
                        if expr_node:
                            return self._get_node_range(expr_node)
                    return self._get_node_range(node.parent.parent)
            return (0, 0)
        return self._find_element_by_query(code, self.templates[CodeElementType.STATIC_PROPERTY.value]['find_one'].format(property_name=name))

    def _handle_property(self, code: str, name: str, parent_name: Optional[str]) -> Tuple[int, int]:
        """Handle finding an instance property."""
        if parent_name:
            init_template = self.templates[CodeElementType.METHOD.value]['find_one'].format(method_name='__init__')
            (root, code_bytes) = self.ast_handler.parse(code)
            class_template = self.templates[CodeElementType.CLASS.value]['find_one'].format(class_name=parent_name)
            class_nodes = self._execute_query(root, code_bytes, class_template)
            class_node = None
            for (node, capture_name) in class_nodes:
                if capture_name == 'class':
                    class_node = node
                    break
            if not class_node:
                return (0, 0)
            init_nodes = self._execute_query(class_node, code_bytes, init_template)
            init_node = None
            for (node, capture_name) in init_nodes:
                if capture_name == 'method_name':
                    init_node = self._find_parent_of_type(node, 'function_definition')
                    break
            if not init_node:
                return (0, 0)
            property_query = self.additional_queries['instance_property_in_init'].format(property_name=name)
            property_nodes = self._execute_query(init_node, code_bytes, property_query)
            for (node, capture_name) in property_nodes:
                if capture_name == 'prop_name':
                    assignment_node = self._find_parent_of_type(node, 'assignment')
                    if assignment_node:
                        return self._get_node_range(assignment_node)
            return (0, 0)
        return (0, 0)

    def _handle_import(self, code: str, name: str, parent_name: Optional[str]) -> Tuple[int, int]:
        """Handle finding import statements."""
        (root, code_bytes) = self.ast_handler.parse(code)
        if 'find_all' not in self.templates[CodeElementType.IMPORT.value]:
            return (0, 0)
        query = self.templates[CodeElementType.IMPORT.value]['find_all']
        nodes = self._execute_query(root, code_bytes, query)
        if not nodes:
            return (0, 0)
        import_nodes = []
        for (node, capture_name) in nodes:
            if capture_name == 'import':
                import_nodes.append(node)
        if not import_nodes:
            return (0, 0)
        import_nodes.sort(key=lambda n: n.start_point[0])
        return (import_nodes[0].start_point[0] + 1, import_nodes[-1].end_point[0] + 1)

    def _find_element_by_query(self, code: str, query: str) -> Tuple[int, int]:
        """
        Find an element using a tree-sitter query.
        
        Args:
            code: Source code as string
            query: Tree-sitter query
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(code)
            nodes = self._execute_query(root, code_bytes, query)
            element_node = None
            for (node, capture_name) in nodes:
                if capture_name.endswith('_name'):
                    element_node = self._find_parent_of_type(node, self._get_parent_node_type(capture_name))
                    if element_node:
                        break
                elif capture_name in self._get_element_capture_names():
                    element_node = node
                    break
            if element_node:
                return self._get_node_range(element_node)
            return (0, 0)
        except Exception as e:
            logger.debug(f'Error in find_element_by_query: {str(e)}')
            return (0, 0)

    def _get_parent_node_type(self, capture_name: str) -> str:
        """
        Get the parent node type for a capture name.
        
        Args:
            capture_name: Capture name (e.g., 'func_name', 'class_name')
            
        Returns:
            Parent node type (e.g., 'function_definition', 'class_definition')
        """
        if capture_name == 'func_name':
            return 'function_definition'
        elif capture_name == 'class_name':
            return 'class_definition'
        elif capture_name == 'method_name':
            return 'function_definition'
        elif capture_name == 'property_name':
            return 'function_definition'
        elif capture_name == 'prop_name':
            return 'assignment'
        else:
            return 'module'

    def _get_element_capture_names(self) -> List[str]:
        """
        Get the list of element capture names.

        Returns:
        List of element capture names
        """
        return ['class', 'function', 'method', 'property', 'import', 'property_getter', 'property_setter', 'static_property']

    def find_element_in_parent(self, code: str, parent_type: str, parent_name: str, element_type: str, element_name: str, template_key: str=None) -> Tuple[int, int]:
        """
        Find an element within a parent element.
        
        Args:
            code: Source code as string
            parent_type: Type of parent element
            parent_name: Name of parent element
            element_type: Type of element to find
            element_name: Name of element to find
            template_key: Optional alternate template key
            
        Returns:
            Tuple of (start_line, end_line) or (0, 0) if not found
        """
        try:
            parent_template = self.templates[parent_type]['find_one'].format(**{f'{parent_type.lower()}_name': parent_name})
            (root, code_bytes) = self.ast_handler.parse(code)
            parent_nodes = self._execute_query(root, code_bytes, parent_template)
            parent_node = None
            for (node, capture_name) in parent_nodes:
                if capture_name == parent_type or capture_name == parent_type.lower():
                    parent_node = node
                    break
            if not parent_node:
                return (0, 0)
            key = template_key or element_type
            if key not in self.templates or 'find_one' not in self.templates[key]:
                return (0, 0)
            param_name = 'property_name' if element_type in [CodeElementType.PROPERTY_GETTER.value, CodeElementType.PROPERTY_SETTER.value] else f'{element_type.lower()}_name'
            element_template = self.templates[key]['find_one'].format(**{param_name: element_name})
            element_nodes = self._execute_query(parent_node, code_bytes, element_template)
            for (node, capture_name) in element_nodes:
                if capture_name == element_type or capture_name == key or capture_name == key.lower():
                    return self._get_node_range(node)
            return (0, 0)
        except Exception as e:
            logger.debug(f'Error in find_element_in_parent: {str(e)}')
            return (0, 0)

    def get_elements_by_type(self, code: str, element_type: str) -> List[Dict[str, Any]]:
        """
        Get all elements of the specified type from the code.
        
        Args:
            code: Source code as string
            element_type: Type of elements to find
            
        Returns:
            List of dictionaries with element information
        """
        if element_type not in self.templates or 'find_all' not in self.templates[element_type]:
            return []
        template = self.templates[element_type]['find_all']
        (root, code_bytes) = self.ast_handler.parse(code)
        nodes = self._execute_query(root, code_bytes, template)
        result = []
        current_element = None
        for (node, capture_name) in nodes:
            if capture_name == element_type or capture_name in self._get_element_capture_names():
                if current_element:
                    result.append(current_element)
                current_element = {'node': node, 'type': element_type, 'range': self._get_node_range(node), 'content': self.get_node_content(node, code_bytes)}
            elif capture_name.endswith('_name') and current_element:
                current_element['name'] = self.get_node_content(node, code_bytes)
        if current_element:
            result.append(current_element)
        return result

    def get_class_decorators(self, code: str, class_name: str) -> List[str]:
        """
        Get a list of decorators for a class.
        
        Args:
            code: Source code as string
            class_name: Name of the class
            
        Returns:
            List of decorator strings
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(code)
            query = r"""
            (
                decorated_definition 
                decorator: (decorator) @dec
                definition: (class_definition 
                    name: (identifier) @class_name (#eq? @class_name "{class_name}")
                )
            )
            """.format(class_name=class_name)
            nodes = self._execute_query(root, code_bytes, query)
            decorator_nodes = [node for (node, capture_name) in nodes if capture_name == 'dec']
            return [self.get_node_content(node, code_bytes) for node in decorator_nodes]
        except Exception as e:
            logger.debug(f'Error getting class decorators: {str(e)}')
            return []

    def get_decorators(self, code: str, element_name: str, class_name: Optional[str]=None) -> List[str]:
        """
        Get a list of decorators for a function or method.
        
        Args:
            code: Source code as string
            element_name: Name of the function or method
            class_name: Optional name of the class (for methods)
            
        Returns:
            List of decorator strings
        """
        # First try using the specific decorator query
        try:
            if class_name:
                # Use regex to find the method and its decorators
                lines = code.splitlines()
                class_start = 0
                class_end = len(lines)
                
                # Find class boundaries
                class_pattern = re.compile(rf'class\s+{re.escape(class_name)}\s*[:(]')
                for i, line in enumerate(lines):
                    if class_pattern.match(line.strip()):
                        class_start = i
                        # Find class end (next line with same or less indentation)
                        indent = len(line) - len(line.lstrip())
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= indent:
                                class_end = j
                                break
                        break
                
                # Look for the method and decorators within class boundaries
                method_pattern = re.compile(rf'\s+def\s+{re.escape(element_name)}\s*\(')
                decorators = []
                
                for i in range(class_start, class_end):
                    if method_pattern.match(lines[i]):
                        # Found the method, now look backward for decorators
                        method_indent = len(lines[i]) - len(lines[i].lstrip())
                        j = i - 1
                        while j >= class_start:
                            line = lines[j].strip()
                            if line.startswith('@') and len(lines[j]) - len(lines[j].lstrip()) == method_indent:
                                decorators.insert(0, line)
                            elif line and len(lines[j]) - len(lines[j].lstrip()) == method_indent:
                                break
                            j -= 1
                        break
                
                if decorators:
                    return decorators
            
            # If regex approach didn't work or we're looking for standalone function, try tree-sitter
            (root, code_bytes) = self.ast_handler.parse(code)
            
            if class_name:
                # First find the class
                class_query = self.templates[CodeElementType.CLASS.value]['find_one'].format(class_name=class_name)
                class_nodes = self._execute_query(root, code_bytes, class_query)
                class_node = None
                for (node, capture_name) in class_nodes:
                    if capture_name == 'class':
                        class_node = node
                        break
                
                if not class_node:
                    return []
                
                # Use the additional query for method decorators
                if 'decorator_for_method' in self.additional_queries:
                    decorator_query = self.additional_queries['decorator_for_method'].format(method_name=element_name)
                    nodes = self._execute_query(class_node, code_bytes, decorator_query)
                else:
                    # Fallback to generic query
                    query = r"""
                    (
                        decorated_definition 
                        decorator: (decorator) @dec
                        definition: (function_definition 
                            name: (identifier) @method_name (#eq? @method_name "{method_name}")
                        )
                    )
                    """.format(method_name=element_name)
                    nodes = self._execute_query(class_node, code_bytes, query)
            else:
                # For standalone functions
                query = r"""
                (
                    decorated_definition 
                    decorator: (decorator) @dec
                    definition: (function_definition 
                        name: (identifier) @func_name (#eq? @func_name "{func_name}")
                    )
                )
                """.format(func_name=element_name)
                nodes = self._execute_query(root, code_bytes, query)
            
            decorator_nodes = [node for (node, capture_name) in nodes if capture_name == 'dec']
            return [self.get_node_content(node, code_bytes) for node in decorator_nodes]
        except Exception as e:
            logger.debug(f'Error getting decorators: {str(e)}')
            
            # Fallback to regex if tree-sitter failed
            try:
                lines = code.splitlines()
                
                if class_name:
                    # First find the class
                    class_pattern = re.compile(rf'class\s+{re.escape(class_name)}\s*[:(]')
                    class_start = -1
                    class_end = len(lines)
                    
                    for i, line in enumerate(lines):
                        if class_pattern.match(line.strip()):
                            class_start = i
                            indent = len(line) - len(line.lstrip())
                            for j in range(i + 1, len(lines)):
                                if lines[j].strip() and len(lines[j]) - len(lines[j].lstrip()) <= indent:
                                    class_end = j
                                    break
                            break
                    
                    if class_start < 0:
                        return []
                    
                    search_range = range(class_start, class_end)
                else:
                    search_range = range(len(lines))
                
                # Find the method/function
                method_pattern = re.compile(rf'(^|\s+)def\s+{re.escape(element_name)}\s*\(')
                for i in search_range:
                    if method_pattern.search(lines[i]):
                        # Found method, look backward for decorators
                        decorators = []
                        indent = len(lines[i]) - len(lines[i].lstrip())
                        j = i - 1
                        while j >= 0 and j in search_range:
                            line = lines[j].strip()
                            current_indent = len(lines[j]) - len(lines[j].lstrip())
                            if line.startswith('@') and current_indent == indent:
                                decorators.insert(0, line)
                            elif line and current_indent <= indent and not line.startswith('@'):
                                break
                            j -= 1
                        return decorators
            except Exception as e:
                logger.debug(f'Error in regex approach for decorators: {str(e)}')
            
            return []

    def get_function_parameters(self, method_content: str, method_name: str, class_name: Optional[str]=None) -> List[Dict[str, Any]]:
        """
        Get parameters for a function or method.
        
        Args:
            method_content: Content of the function or method
            method_name: Name of the function or method
            class_name: Optional name of the class (for methods)
            
        Returns:
            List of parameter dictionaries with name, type, and optional info
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(method_content)
            query = r"""
            (
                function_definition
                name: (identifier) @func_name (#eq? @func_name "{func_name}")
                parameters: (parameters) @params
            )
            """.format(func_name=method_name)
            nodes = self._execute_query(root, code_bytes, query)
            params_node = None
            for (node, capture_name) in nodes:
                if capture_name == 'params':
                    params_node = node
                    break
            if not params_node:
                return []
            param_query = r"""
            (
                parameters
                [(identifier) @param
                 (typed_parameter
                    name: (identifier) @typed_param_name
                    type: (_) @typed_param_type)
                 (default_parameter
                    name: (identifier) @default_param_name
                    value: (_) @default_param_value)
                 (typed_default_parameter
                    name: (identifier) @typed_default_param_name
                    type: (_) @typed_default_param_type
                    value: (_) @typed_default_param_value)]
            )
            """
            param_nodes = self._execute_query(params_node, code_bytes, param_query)
            parameters = []
            current_param = None
            for (node, capture_name) in param_nodes:
                if capture_name == 'param':
                    name = self.get_node_content(node, code_bytes)
                    if name != 'self' or not class_name:
                        parameters.append({'name': name, 'type': None})
                elif capture_name == 'typed_param_name':
                    name = self.get_node_content(node, code_bytes)
                    if name != 'self' or not class_name:
                        current_param = {'name': name, 'type': None}
                        parameters.append(current_param)
                elif capture_name == 'typed_param_type' and current_param:
                    current_param['type'] = self.get_node_content(node, code_bytes)
                elif capture_name == 'default_param_name':
                    name = self.get_node_content(node, code_bytes)
                    if name != 'self' or not class_name:
                        current_param = {'name': name, 'type': None, 'optional': True}
                        parameters.append(current_param)
                elif capture_name == 'default_param_value' and current_param:
                    current_param['default'] = self.get_node_content(node, code_bytes)
                elif capture_name == 'typed_default_param_name':
                    name = self.get_node_content(node, code_bytes)
                    if name != 'self' or not class_name:
                        current_param = {'name': name, 'type': None, 'optional': True}
                        parameters.append(current_param)
                elif capture_name == 'typed_default_param_type' and current_param:
                    current_param['type'] = self.get_node_content(node, code_bytes)
                elif capture_name == 'typed_default_param_value' and current_param:
                    current_param['default'] = self.get_node_content(node, code_bytes)
            return parameters
        except Exception as e:
            logger.debug(f'Error getting function parameters: {str(e)}')
            parameters = []
            param_pattern = r'def\s+' + re.escape(method_name) + r'\s*\(([^)]*)\)'
            match = re.search(param_pattern, method_content)
            if match:
                param_list = match.group(1).split(',')
                for (i, param) in enumerate(param_list):
                    param = param.strip()
                    if not param:
                        continue
                    if i == 0 and param == 'self' and class_name:
                        continue
                    param_dict = {'name': param, 'type': None}
                    if ':' in param:
                        (name_part, type_part) = param.split(':', 1)
                        param_dict['name'] = name_part.strip()
                        param_dict['type'] = type_part.strip()
                    if '=' in param_dict['name']:
                        (name_part, value_part) = param_dict['name'].split('=', 1)
                        param_dict['name'] = name_part.strip()
                        param_dict['default'] = value_part.strip()
                        param_dict['optional'] = True
                    parameters.append(param_dict)
            return parameters

    def get_function_return_info(self, method_content: str, method_name: str, class_name: Optional[str]=None) -> Dict[str, Any]:
        """
        Get return type information for a function or method.
        
        Args:
            method_content: Content of the function or method
            method_name: Name of the function or method
            class_name: Optional name of the class (for methods)
            
        Returns:
            Dictionary with return_type and return_values
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(method_content)
            return_type_query = r"""
            (
                function_definition
                name: (identifier) @func_name (#eq? @func_name "{func_name}")
                return_type: (_) @return_type
            )
            """.format(func_name=method_name)
            return_type_nodes = self._execute_query(root, code_bytes, return_type_query)
            return_type = None
            for (node, capture_name) in return_type_nodes:
                if capture_name == 'return_type':
                    return_type = self.get_node_content(node, code_bytes)
                    break
            return_stmt_query = r"""
            (
                function_definition
                name: (identifier) @func_name (#eq? @func_name "{func_name}")
                body: (block 
                    (return_statement 
                        value: (_) @return_value)
                )
            )
            """.format(func_name=method_name)
            return_stmt_nodes = self._execute_query(root, code_bytes, return_stmt_query)
            return_values = []
            for (node, capture_name) in return_stmt_nodes:
                if capture_name == 'return_value':
                    return_values.append(self.get_node_content(node, code_bytes))
            return {'return_type': return_type, 'return_values': return_values}
        except Exception as e:
            logger.debug(f'Error getting function return info: {str(e)}')
            return_type = None
            return_values = []
            return_type_pattern = r'def\s+' + re.escape(method_name) + r'\s*\([^)]*\)\s*->\s*([^:]+):'
            type_match = re.search(return_type_pattern, method_content)
            if type_match:
                return_type = type_match.group(1).strip()
            return_stmt_pattern = r'return\s+([^;\n]+)'
            return_matches = re.finditer(return_stmt_pattern, method_content)
            for match in return_matches:
                return_values.append(match.group(1).strip())
            return {'return_type': return_type, 'return_values': return_values}

    def get_node_content(self, node: Node, code_bytes: bytes) -> str:
        """
        Get the content of a node.
        
        Args:
            node: Tree-sitter node
            code_bytes: Source code as bytes
            
        Returns:
            Content of the node as string
        """
        return self.ast_handler.get_node_text(node, code_bytes)

    def get_node_range(self, node: Node) -> Tuple[int, int]:
        """
        Get the line range of a node.
        
        Args:
            node: Tree-sitter node
            
        Returns:
            Tuple of (start_line, end_line)
        """
        return self._get_node_range(node)

    def _get_node_range(self, node: Node) -> Tuple[int, int]:
        """Internal method to get node range."""
        return (node.start_point[0] + 1, node.end_point[0] + 1)

    def _execute_query(self, node: Node, code_bytes: bytes, query_string: str) -> List[Tuple[Node, str]]:
        """Execute a tree-sitter query and return results."""
        try:
            return self.ast_handler.execute_query(query_string, node, code_bytes)
        except Exception as e:
            logger.debug(f'Error executing query: {str(e)}')
            return []

    def _find_parent_of_type(self, node: Node, node_type: str) -> Optional[Node]:
        """Find the nearest parent of a specific type."""
        current = node
        while current:
            if current.type == node_type:
                return current
            current = current.parent
        return None

    def is_class_definition(self, node: Optional[Node], code_bytes: bytes) -> bool:
        """Check if a node is a class definition."""
        if not node:
            return False
        return node.type == 'class_definition'

    def is_function_definition(self, node: Optional[Node], code_bytes: bytes) -> bool:
        """Check if a node is a function definition."""
        if not node:
            return False
        return node.type == 'function_definition'

    def is_method_definition(self, node: Optional[Node], code_bytes: bytes) -> bool:
        """Check if a node is a method definition."""
        if not node or node.type != 'function_definition':
            return False
        params = node.child_by_field_name('parameters')
        if not params or not params.named_children:
            return False
        first_param = params.named_children[0]
        if first_param.type == 'identifier':
            param_name = self.get_node_content(first_param, code_bytes)
            return param_name == 'self'
        return False

    def determine_element_type(self, node: Node, code_bytes: bytes) -> str:
        """Determine element type from node."""
        if not node:
            return CodeElementType.MODULE.value
        if node.type == 'class_definition':
            return CodeElementType.CLASS.value
        if node.type == 'function_definition':
            if self.is_method_definition(node, code_bytes):
                return CodeElementType.METHOD.value
            parent = node.parent
            if parent and parent.type == 'decorated_definition':
                decorator = parent.child_by_field_name('decorator')
                if decorator:
                    if decorator.type == 'decorator':
                        name_node = decorator.child_by_field_name('name')
                        if name_node and name_node.type == 'identifier':
                            decorator_name = self.get_node_content(name_node, code_bytes)
                            if decorator_name == 'property':
                                return CodeElementType.PROPERTY_GETTER.value
                    if decorator.type == 'decorator':
                        name_node = decorator.child_by_field_name('name')
                        if name_node and name_node.type == 'attribute':
                            attr_node = name_node.child_by_field_name('attribute')
                            if attr_node and self.get_node_content(attr_node, code_bytes) == 'setter':
                                return CodeElementType.PROPERTY_SETTER.value
            return CodeElementType.FUNCTION.value
        if node.type == 'assignment':
            left = node.child_by_field_name('left')
            if left and left.type == 'attribute':
                obj = left.child_by_field_name('object')
                if obj and obj.type == 'identifier' and (self.get_node_content(obj, code_bytes) == 'self'):
                    return CodeElementType.PROPERTY.value
            elif left and left.type == 'identifier':
                return CodeElementType.STATIC_PROPERTY.value
        if node.type == 'import_statement' or node.type == 'import_from_statement':
            return CodeElementType.IMPORT.value
        return CodeElementType.MODULE.value

    def get_imports(self, code: str) -> Dict[str, Any]:
        """
        Get imports from code.
        
        Args:
            code: Source code as string
            
        Returns:
            Dictionary with import information
        """
        try:
            (root, code_bytes) = self.ast_handler.parse(code)
            import_query = '(import_statement) @import (import_from_statement) @import_from'
            import_nodes = self._execute_query(root, code_bytes, import_query)
            if not import_nodes:
                return {}
            import_nodes = [node for (node, _) in import_nodes]
            import_nodes.sort(key=lambda n: n.start_point[0])
            start_line = import_nodes[0].start_point[0] + 1
            end_line = import_nodes[-1].end_point[0] + 1
            lines = code.splitlines()
            content = '\n'.join(lines[start_line - 1:end_line])
            import_lines = [self.get_node_content(node, code_bytes) for node in import_nodes]
            return {'content': content, 'start_line': start_line, 'end_line': end_line, 'statements': import_lines}
        except Exception as e:
            logger.debug(f'Error getting imports: {str(e)}')
            return {}

    def determine_element_type(self, decorators: List[str], is_method: bool=False) -> str:
        """
        Determine element type from decorators and context.
        This method exists for compatibility with extraction_service.
        
        Args:
            decorators: List of decorator strings
            is_method: Whether the element is a method
            
        Returns:
            Element type string from CodeElementType
        """
        if not decorators:
            return CodeElementType.METHOD.value if is_method else CodeElementType.FUNCTION.value
        for decorator in decorators:
            if '@property' in decorator:
                return CodeElementType.PROPERTY_GETTER.value
            if '.setter' in decorator:
                return CodeElementType.PROPERTY_SETTER.value
        return CodeElementType.METHOD.value if is_method else CodeElementType.FUNCTION.value

    def _extract_decorator_name(self, decorator: str) -> str:
        """
        Extract decorator name from decorator string.
        This method exists for compatibility with extraction_service.
        
        Args:
            decorator: Decorator string (e.g., '@property', '@staticmethod')
            
        Returns:
            Decorator name without '@' prefix
        """
        if not decorator:
            return ''
        name = decorator.strip()
        if name.startswith('@'):
            name = name[1:]
        name = name.split('(')[0].strip()
        if '.' in name:
            return name.split('.')[1].strip()
        return name.strip()