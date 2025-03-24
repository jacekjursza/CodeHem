"""
Method extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class MethodExtractor(BaseExtractor):
    """Method extractor using language-specific handlers."""

    @property
    def element_type(self) -> CodeElementType:
        """Get the element type this extractor handles."""
        return CodeElementType.METHOD

    def supports_language(self, language_code: str) -> bool:
        """Check if this extractor supports the given language."""
        return language_code.lower() in self.handlers

    def extract(self, code: str, context: Optional[Dict[str, Any]]=None) -> List[Dict]:
        """
        Extract methods from the provided code.
        
        Args:
            code: The source code to extract from
            context: Optional context information for the extraction
            
        Returns:
            List of extracted methods as dictionaries
        """
        context = context or {}
        language_code = context.get('language_code', 'python').lower()
        class_name = context.get('class_name')
        if not self.supports_language(language_code):
            return []
        handler = self.handlers[language_code]
        if handler.custom_extract:
            return handler.extract(code, context)
        methods = self._extract_with_patterns(code, handler, context)
        if class_name and methods:
            filtered_methods = []
            for method in methods:
                if method.get('class_name') == class_name:
                    filtered_methods.append(method)
            return filtered_methods
        return methods

    def _extract_with_patterns(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract using TreeSitter first, fall back to regex if needed."""
        if handler.tree_sitter_query:
            methods = self._extract_with_tree_sitter(code, handler, context)
            if methods:
                return methods
        if handler.regexp_pattern:
            return self._extract_with_regex(code, handler, context)
        return []

    def _extract_with_tree_sitter(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract methods using TreeSitter."""
        ast_handler = self._get_ast_handler(handler.language_code)
        if not ast_handler:
            return []
        try:
            (root, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
            methods = []

            # Process method nodes and their names
            method_nodes = {}

            # First pass: collect method nodes and names
            for (node, capture_name) in query_results:
                if capture_name == 'method_def':
                    name_node = ast_handler.find_child_by_field_name(node, 'name')
                    if name_node:
                        method_name = ast_handler.get_node_text(name_node, code_bytes)
                        method_nodes[method_name] = node
                elif capture_name == 'method_name':
                    method_name = ast_handler.get_node_text(node, code_bytes)
                    method_node = ast_handler.find_parent_of_type(node, 'function_definition')
                    if method_node:
                        method_nodes[method_name] = method_node

            # Second pass: process each method
            for method_name, method_node in method_nodes.items():
                (start_line, end_line) = ast_handler.get_node_range(method_node)
                content = ast_handler.get_node_text(method_node, code_bytes)

                # Find class name
                class_name = None
                if context.get('class_name'):
                    class_name = context.get('class_name')
                else:
                    class_node = ast_handler.find_parent_of_type(method_node, 'class_definition')
                    if class_node:
                        class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                        if class_name_node:
                            class_name = ast_handler.get_node_text(class_name_node, code_bytes)

                # Extract decorators
                parent_node = method_node.parent
                decorators = []
                if parent_node and parent_node.type == 'decorated_definition':
                    for child_idx in range(parent_node.named_child_count):
                        child = parent_node.named_child(child_idx)
                        if child and child.type == 'decorator':
                            name_node = ast_handler.find_child_by_field_name(child, 'name')
                            if name_node:
                                dec_name = ast_handler.get_node_text(name_node, code_bytes)
                                dec_content = ast_handler.get_node_text(child, code_bytes)
                                decorators.append({'name': dec_name, 'content': dec_content})
                    content = ast_handler.get_node_text(parent_node, code_bytes)
                    start_line = parent_node.start_point[0]
                    end_line = parent_node.end_point[0]

                # Extract parameters
                parameters = []
                params_node = ast_handler.find_child_by_field_name(method_node, 'parameters')
                if params_node:
                    for i in range(params_node.named_child_count):
                        param_node = params_node.named_child(i)
                        if i == 0 and ast_handler.get_node_text(param_node, code_bytes) == 'self':
                            # Skip self parameter
                            continue

                        param_info = self._extract_parameter(param_node, code_bytes, ast_handler)
                        if param_info:
                            parameters.append(param_info)

                # Extract return type
                return_type = None
                return_type_node = ast_handler.find_child_by_field_name(method_node, 'return_type')
                if return_type_node:
                    return_type = ast_handler.get_node_text(return_type_node, code_bytes)

                # Extract return values
                return_values = []
                body_node = ast_handler.find_child_by_field_name(method_node, 'body')
                if body_node:
                    try:
                        return_query = '(return_statement) @return_stmt'
                        return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                        for (return_node, _) in return_results:
                            stmt_text = ast_handler.get_node_text(return_node, code_bytes)
                            if stmt_text.startswith('return '):
                                return_values.append(stmt_text[7:].strip())
                    except Exception:
                        pass

                # Determine method type
                element_type = 'method'
                property_name = None
                for decorator in decorators:
                    if decorator.get('name') == 'property':
                        element_type = 'property_getter'
                        property_name = method_name
                    elif decorator.get('name', '').endswith('.setter'):
                        element_type = 'property_setter'
                        property_name = decorator.get('name').split('.')[0]

                # Create method info
                method_info = {
                    'type': element_type,
                    'name': method_name,
                    'content': content,
                    'class_name': class_name,
                    'range': {
                        'start': {'line': start_line, 'column': method_node.start_point[1]},
                        'end': {'line': end_line, 'column': method_node.end_point[1]}
                    },
                    'decorators': decorators,
                    'parameters': parameters,
                    'return_info': {
                        'return_type': return_type,
                        'return_values': return_values
                    },
                    'property_name': property_name
                }

                methods.append(method_info)

            return methods
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return []

    def _extract_decorators(self, method_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract decorators from a method node.
        
        Args:
            method_node: Method node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of decorator dictionaries
        """
        decorators = []
        parent_node = method_node.parent
        
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

    def _extract_parameters(self, method_node, code_bytes, ast_handler) -> List[Dict]:
        """
        Extract detailed parameter information from a method.
        
        Args:
            method_node: Method node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            List of parameter dictionaries with name, type, and default value
        """
        parameters = []
        
        # Find parameters node
        params_node = None
        for child_idx in range(method_node.named_child_count):
            child = method_node.named_child(child_idx)
            if child.type == 'parameters':
                params_node = child
                break
        
        if not params_node:
            return parameters
        
        # Process each parameter
        for child_idx in range(params_node.named_child_count):
            child = params_node.named_child(child_idx)
            
            if child.type == 'identifier':
                # Simple parameter (e.g., self, x)
                name = ast_handler.get_node_text(child, code_bytes)
                if name != 'self':  # Skip 'self' in parameter list
                    parameters.append({'name': name, 'type': None})
                
            elif child.type == 'typed_parameter':
                # Parameter with type annotation (e.g., x: int)
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    if name != 'self':  # Skip 'self' in parameter list
                        param_dict = {'name': name, 'type': None}
                        
                        if type_node:
                            param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                        
                        parameters.append(param_dict)
                
            elif child.type == 'default_parameter':
                # Parameter with default value (e.g., x=10)
                name_node = child.child_by_field_name('name')
                value_node = child.child_by_field_name('value')
                
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    if name != 'self':  # Skip 'self' in parameter list
                        param_dict = {'name': name, 'type': None, 'optional': True}
                        
                        if value_node:
                            param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                        
                        parameters.append(param_dict)
                
            elif child.type == 'typed_default_parameter':
                # Parameter with type and default value (e.g., x: int = 10)
                name_node = child.child_by_field_name('name')
                type_node = child.child_by_field_name('type')
                value_node = child.child_by_field_name('value')
                
                if name_node:
                    name = ast_handler.get_node_text(name_node, code_bytes)
                    if name != 'self':  # Skip 'self' in parameter list
                        param_dict = {'name': name, 'type': None, 'optional': True}
                        
                        if type_node:
                            param_dict['type'] = ast_handler.get_node_text(type_node, code_bytes)
                        
                        if value_node:
                            param_dict['default'] = ast_handler.get_node_text(value_node, code_bytes)
                        
                        parameters.append(param_dict)
        
        return parameters

    def _extract_return_info(self, method_node, code_bytes, ast_handler) -> Dict:
        """
        Extract return type information from a method.
        
        Args:
            method_node: Method node
            code_bytes: Source code as bytes
            ast_handler: AST handler
            
        Returns:
            Dictionary with return_type and return_values
        """
        return_type = None
        return_values = []
        
        # Get return type annotation
        return_type_node = method_node.child_by_field_name('return_type')
        if return_type_node:
            return_type = ast_handler.get_node_text(return_type_node, code_bytes)
        
        # Get return statements - using more robust approach
        body_node = method_node.child_by_field_name('body')
        if body_node:
            try:
                # Using a more flexible query that doesn't rely on a specific field name
                return_query = "(return_statement (_) @return_value)"
                return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                
                for node, capture_name in return_results:
                    if capture_name == 'return_value':
                        return_values.append(ast_handler.get_node_text(node, code_bytes))
            except Exception as e:
                # If the query fails, try an alternative approach
                try:
                    # Alternative: Just capture the return statement and extract content manually
                    alt_query = "(return_statement) @return_stmt"
                    return_stmts = ast_handler.execute_query(alt_query, body_node, code_bytes)
                    
                    for node, capture_name in return_stmts:
                        if capture_name == 'return_stmt':
                            stmt_text = ast_handler.get_node_text(node, code_bytes)
                            # Extract the value after 'return' keyword
                            if stmt_text.startswith('return '):
                                return_values.append(stmt_text[7:].strip())
                except Exception:
                    # If all tree-sitter approaches fail, use regex as last resort
                    method_text = ast_handler.get_node_text(method_node, code_bytes)
                    return_regex = r'return\s+(.+?)(?:\n|$)'
                    for match in re.finditer(return_regex, method_text):
                        return_values.append(match.group(1).strip())
        
        return {
            'return_type': return_type,
            'return_values': return_values
        }

    def _extract_with_regex(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract methods using regex."""
        class_name = context.get('class_name')
        if class_name:
            class_pattern = 'class\\s+' + re.escape(class_name) + '(?:\\s*\\([^)]*\\))?\\s*:(.*?)(?=\\n(?:class|def\\s+\\w+\\s*\\([^s]|$))'
            class_match = re.search(class_pattern, code, re.DOTALL)
            if not class_match:
                return []
            code_to_search = class_match.group(1)
            base_indent = ' ' * 4
        else:
            code_to_search = code
            base_indent = ''
        try:
            if class_name:
                pattern = f'{re.escape(base_indent)}' + handler.regexp_pattern
            else:
                pattern = handler.regexp_pattern
            matches = re.finditer(pattern, code_to_search, re.DOTALL)
            methods = []
            for match in matches:
                name = match.group(1)
                content = match.group(0)
                if class_name:
                    start_pos = class_match.start(1) + match.start()
                    end_pos = class_match.start(1) + match.end()
                else:
                    start_pos = match.start()
                    end_pos = match.end()
                lines_before = code[:start_pos].count('\n')
                last_newline = code[:start_pos].rfind('\n')
                start_column = start_pos - last_newline - 1 if last_newline >= 0 else start_pos
                lines_total = code[:end_pos].count('\n')
                last_newline_end = code[:end_pos].rfind('\n')
                end_column = end_pos - last_newline_end - 1 if last_newline_end >= 0 else end_pos
                
                # Extract decorators
                decorator_lines = []
                method_line = None
                for i, line in enumerate(content.splitlines()):
                    if line.strip().startswith('@'):
                        decorator_lines.append(line.strip())
                    elif line.strip().startswith('def '):
                        method_line = i
                        break
                
                decorators = []
                for decorator in decorator_lines:
                    name = decorator[1:].split('(')[0] if '(' in decorator else decorator[1:]
                    decorators.append({'name': name, 'content': decorator})
                
                # Determine if this is a property getter or setter
                is_property = False
                is_property_setter = False
                property_name = None
                
                for decorator in decorators:
                    if decorator.get('name') == 'property':
                        is_property = True
                    elif decorator.get('name', '').endswith('.setter'):
                        is_property_setter = True
                        property_name = decorator.get('name').split('.')[0]
                
                element_type = 'method'
                if is_property:
                    element_type = 'property_getter'
                elif is_property_setter:
                    element_type = 'property_setter'
                
                # Extract parameters
                param_pattern = r'def\s+\w+\s*\((.*?)\)'
                param_match = re.search(param_pattern, content)
                parameters = []
                if param_match:
                    params_str = param_match.group(1)
                    param_list = [p.strip() for p in params_str.split(',') if p.strip()]
                    for param in param_list:
                        if param == 'self':  # Skip 'self' in parameter list
                            continue
                            
                        param_dict = {'name': param, 'type': None}
                        
                        # Check for type annotation
                        if ':' in param:
                            name_part, type_part = param.split(':', 1)
                            param_dict['name'] = name_part.strip()
                            param_dict['type'] = type_part.strip()
                        
                        # Check for default value
                        if '=' in param_dict['name']:
                            name_part, value_part = param_dict['name'].split('=', 1)
                            param_dict['name'] = name_part.strip()
                            param_dict['default'] = value_part.strip()
                            param_dict['optional'] = True
                        
                        parameters.append(param_dict)
                
                # Extract return type
                return_info = {'return_type': None, 'return_values': []}
                return_type_pattern = r'def\s+\w+\s*\([^)]*\)\s*->\s*([^:]+):'
                return_type_match = re.search(return_type_pattern, content)
                if return_type_match:
                    return_info['return_type'] = return_type_match.group(1).strip()
                
                # Extract return values
                return_pattern = r'return\s+([^;]+)'
                return_matches = re.finditer(return_pattern, content)
                for return_match in return_matches:
                    return_info['return_values'].append(return_match.group(1).strip())
                
                methods.append({
                    'type': element_type, 
                    'name': name, 
                    'content': content, 
                    'class_name': class_name,
                    'range': {
                        'start': {'line': lines_before, 'column': start_column}, 
                        'end': {'line': lines_total, 'column': end_column}
                    },
                    'decorators': decorators,
                    'parameters': parameters,
                    'return_info': return_info,
                    'property_name': property_name
                })
            return methods
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []