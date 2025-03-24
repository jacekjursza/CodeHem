"""
Method extractor that uses language-specific handlers.
"""
from typing import Dict, List, Optional, Any
import re
import logging
from codehem.extractors.base import BaseExtractor
from codehem.models.enums import CodeElementType
from codehem.models.language_handler import LanguageHandler
from codehem.languages.registry import extractor

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
        
        # Filter by class name if provided
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
            (tree, code_bytes) = ast_handler.parse(code)
            query_results = ast_handler.execute_query(handler.tree_sitter_query, tree, code_bytes)
            methods = []

            # First, process regular non-decorated methods
            for match in query_results:
                method_def = None
                method_name = None
                dec_method_def = None
                dec_method_name = None

                for (node, node_type) in match:
                    if node_type == 'method_def':
                        method_def = node
                    elif node_type == 'method_name':
                        method_name = node
                    elif node_type == 'dec_method_def':
                        dec_method_def = node
                    elif node_type == 'dec_method_name':
                        dec_method_name = node

                # Handle regular methods
                if method_def and method_name:
                    name = ast_handler.get_node_text(method_name, code_bytes)
                    content = ast_handler.get_node_text(method_def, code_bytes)
                    class_name = None
                    if context.get('class_name'):
                        class_name = context.get('class_name')
                    else:
                        class_node = ast_handler.find_parent_of_type(method_def, 'class_definition')
                        if class_node:
                            class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                            if class_name_node:
                                class_name = ast_handler.get_node_text(class_name_node, code_bytes)
                    methods.append({'type': 'method', 'name': name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': method_def.start_point[0], 'column': method_def.start_point[1]}, 'end': {'line': method_def.end_point[0], 'column': method_def.end_point[1]}}})

                # Handle decorated methods
                if dec_method_def and dec_method_name:
                    name = ast_handler.get_node_text(dec_method_name, code_bytes)
                    content = ast_handler.get_node_text(dec_method_def, code_bytes)
                    class_name = None
                    if context.get('class_name'):
                        class_name = context.get('class_name')
                    else:
                        class_node = ast_handler.find_parent_of_type(dec_method_def, 'class_definition')
                        if class_node:
                            class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                            if class_name_node:
                                class_name = ast_handler.get_node_text(class_name_node, code_bytes)
                    methods.append({'type': 'method', 'name': name, 'content': content, 'class_name': class_name, 'range': {'start': {'line': dec_method_def.start_point[0], 'column': dec_method_def.start_point[1]}, 'end': {'line': dec_method_def.end_point[0], 'column': dec_method_def.end_point[1]}}})

            return methods
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {e}')
            return []

    def _extract_with_regex(self, code: str, handler: LanguageHandler, context: Dict[str, Any]) -> List[Dict]:
        """Extract methods using regex."""
        class_name = context.get('class_name')
        if class_name:
            # If we know the class name, try to find the class first
            class_pattern = 'class\\s+' + re.escape(class_name) + '(?:\\s*\\([^)]*\\))?\\s*:(.*?)(?=\\n(?:class|def\\s+\\w+\\s*\\([^s]|$))'
            class_match = re.search(class_pattern, code, re.DOTALL)
            if not class_match:
                return []
            code_to_search = class_match.group(1)
            base_indent = ' ' * 4  # Assuming standard Python indentation
        else:
            code_to_search = code
            base_indent = ''
        
        try:
            # Adjust the regex pattern for indentation if we're searching within a class
            if class_name:
                # Make sure the method is indented properly within the class
                pattern = f'{re.escape(base_indent)}' + handler.regexp_pattern
            else:
                pattern = handler.regexp_pattern
                
            matches = re.finditer(pattern, code_to_search, re.DOTALL)
            methods = []
            for match in matches:
                name = match.group(1)
                content = match.group(0)
                
                # For a class method, we need to adjust the position
                if class_name:
                    # Get position relative to the start of the class body
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
                
                methods.append({
                    'type': 'method',
                    'name': name,
                    'content': content,
                    'class_name': class_name,
                    'range': {
                        'start': {'line': lines_before, 'column': start_column},
                        'end': {'line': lines_total, 'column': end_column}
                    }
                })
            return methods
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []