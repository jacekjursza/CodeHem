"""
TypeScript-specific class extractor implementation.
"""
import logging
import re
from typing import Dict, List, Any
from codehem.extractors.template_class_extractor import TemplateClassExtractor
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class TypeScriptClassExtractor(TemplateClassExtractor):
    """TypeScript-specific implementation for class extraction."""
    LANGUAGE_CODE = 'typescript'
    
    def _extract_with_tree_sitter(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract classes using tree-sitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
            
        try:
            root, code_bytes = ast_handler.parse(code)
            # Custom query for classes in case the descriptor isn't properly registered
            class_query = """
            (class_declaration
              name: (type_identifier) @class_name) @class_def
            """
            
            query_results = ast_handler.execute_query(class_query, root, code_bytes)
            return self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return self._extract_with_regex(code, handler, context)
    
    def _extract_with_regex(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract classes using regex as fallback."""
        try:
            # Generic class pattern
            pattern = r'class\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?:extends\s+[A-Za-z_][A-Za-z0-9_]*\s*)?(?:implements\s+[^{]+\s*)?{[^}]*}'
            matches = re.finditer(pattern, code, re.DOTALL)
            return self._process_regex_results(matches, code, context)
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []
    
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results with TypeScript-specific handling."""
        classes = super()._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        
        # If superclass didn't find classes, try with TypeScript-specific approach
        if not classes:
            classes = []
            for node, capture_name in query_results:
                if capture_name == 'class_def':
                    name_node = ast_handler.find_child_by_field_name(node, 'name')
                    if name_node:
                        class_name = ast_handler.get_node_text(name_node, code_bytes)
                        content = ast_handler.get_node_text(node, code_bytes)
                        
                        class_info = {
                            'type': 'class',
                            'name': class_name,
                            'content': content,
                            'range': {
                                'start': {'line': node.start_point[0] + 1, 'column': node.start_point[1]},
                                'end': {'line': node.end_point[0] + 1, 'column': node.end_point[1]}
                            },
                            'decorators': [],
                            'members': {'methods': [], 'properties': [], 'static_properties': []}
                        }
                        classes.append(class_info)
                elif capture_name == 'class_name':
                    class_name = ast_handler.get_node_text(node, code_bytes)
                    class_node = ast_handler.find_parent_of_type(node, 'class_declaration')
                    if class_node:
                        content = ast_handler.get_node_text(class_node, code_bytes)
                        
                        class_info = {
                            'type': 'class',
                            'name': class_name,
                            'content': content,
                            'range': {
                                'start': {'line': class_node.start_point[0] + 1, 'column': class_node.start_point[1]},
                                'end': {'line': class_node.end_point[0] + 1, 'column': class_node.end_point[1]}
                            },
                            'decorators': [],
                            'members': {'methods': [], 'properties': [], 'static_properties': []}
                        }
                        classes.append(class_info)
                
        return classes