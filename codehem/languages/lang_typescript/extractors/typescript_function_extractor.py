"""
TypeScript-specific function extractor implementation.
"""
import logging
import re
from typing import Dict, List, Any
from codehem.extractors.template_function_extractor import TemplateFunctionExtractor
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class TypeScriptFunctionExtractor(TemplateFunctionExtractor):
    """TypeScript-specific implementation for function extraction."""
    LANGUAGE_CODE = 'typescript'
    
    def _extract_with_tree_sitter(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract functions using tree-sitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
            
        try:
            root, code_bytes = ast_handler.parse(code)
            # Custom query for functions and arrow functions
            function_query = """
            (function_declaration
              name: (identifier) @function_name) @function_def
              
            (lexical_declaration
              (variable_declarator
                name: (identifier) @arrow_name
                value: (arrow_function))) @arrow_def
            """
            
            query_results = ast_handler.execute_query(function_query, root, code_bytes)
            functions = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
            
            # Also extract arrow functions
            arrow_functions = self._extract_arrow_functions(code_bytes, ast_handler)
            functions.extend(arrow_functions)
            
            return functions
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return self._extract_with_regex(code, handler, context)
    
    def _extract_with_regex(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract functions using regex as fallback."""
        try:
            functions = []
            
            # Standard function pattern
            func_pattern = r'function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)[^{]*{[^}]*}'
            func_matches = re.finditer(func_pattern, code, re.DOTALL)
            
            for match in func_matches:
                function_name = match.group(1)
                content = match.group(0)
                
                start_pos = match.start()
                end_pos = match.end()
                start_line = code[:start_pos].count('\n') + 1
                end_line = code[:end_pos].count('\n') + 1
                
                function_info = {
                    'type': 'function',
                    'name': function_name,
                    'content': content,
                    'range': {
                        'start': {'line': start_line, 'column': 0},
                        'end': {'line': end_line, 'column': 0}
                    },
                    'parameters': [],
                    'return_info': {'return_type': None, 'return_values': []}
                }
                functions.append(function_info)
            
            # Arrow function pattern
            arrow_pattern = r'const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\([^)]*\)\s*=>\s*{[^}]*}'
            arrow_matches = re.finditer(arrow_pattern, code, re.DOTALL)
            
            for match in arrow_matches:
                function_name = match.group(1)
                content = match.group(0)
                
                start_pos = match.start()
                end_pos = match.end()
                start_line = code[:start_pos].count('\n') + 1
                end_line = code[:end_pos].count('\n') + 1
                
                function_info = {
                    'type': 'function',
                    'name': function_name,
                    'content': content,
                    'range': {
                        'start': {'line': start_line, 'column': 0},
                        'end': {'line': end_line, 'column': 0}
                    },
                    'parameters': [],
                    'return_info': {'return_type': None, 'return_values': []},
                    'is_arrow_function': True
                }
                functions.append(function_info)
                
            return functions
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []
            
    def _extract_arrow_functions(self, code_bytes, ast_handler):
        """Extract arrow functions from TypeScript code."""
        arrow_functions = []
        try:
            # Parse the code
            root, _ = ast_handler.parse(code_bytes)
            
            # Query for arrow functions
            arrow_query = """
            (lexical_declaration
              (variable_declarator
                name: (identifier) @func_name
                value: (arrow_function) @arrow_func))
            """
            
            arrow_results = ast_handler.execute_query(arrow_query, root, code_bytes)
            
            for node, capture_name in arrow_results:
                if capture_name == 'func_name':
                    function_name = ast_handler.get_node_text(node, code_bytes)
                    
                    # Find the variable declarator node
                    declarator_node = node.parent
                    if declarator_node:
                        # Get the entire arrow function declaration
                        declaration_node = declarator_node.parent
                        if declaration_node:
                            content = ast_handler.get_node_text(declaration_node, code_bytes)
                            
                            # Create function info
                            function_info = {
                                'type': 'function',
                                'name': function_name,
                                'content': content,
                                'range': {
                                    'start': {'line': declaration_node.start_point[0] + 1, 'column': declaration_node.start_point[1]},
                                    'end': {'line': declaration_node.end_point[0] + 1, 'column': declaration_node.end_point[1]}
                                },
                                'is_arrow_function': True,
                                'parameters': [],
                                'return_info': {'return_type': None, 'return_values': []}
                            }
                            arrow_functions.append(function_info)
                        
        except Exception as e:
            logger.debug(f"Error extracting arrow functions: {e}")
            
        return arrow_functions