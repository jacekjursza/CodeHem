"""
TypeScript-specific interface extractor implementation.
"""
import logging
import re
from typing import Dict, List, Any
from codehem.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class TypeScriptInterfaceExtractor(TemplateExtractor):
    """TypeScript-specific implementation for interface extraction."""
    ELEMENT_TYPE = CodeElementType.INTERFACE
    LANGUAGE_CODE = 'typescript'
    
    def _extract_with_tree_sitter(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract interfaces using tree-sitter."""
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            return []
            
        try:
            root, code_bytes = ast_handler.parse(code)
            # Custom query for interfaces since we might not have a proper descriptor yet
            interface_query = """
            (interface_declaration
              name: (type_identifier) @interface_name) @interface_def
            """
            
            query_results = ast_handler.execute_query(interface_query, root, code_bytes)
            return self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        except Exception as e:
            logger.debug(f'TreeSitter extraction error: {str(e)}')
            return self._extract_with_regex(code, handler, context)
    
    def _extract_with_regex(self, code: str, handler, context: Dict[str, Any]) -> List[Dict]:
        """Extract interfaces using regex as fallback."""
        try:
            # Generic interface pattern
            pattern = r'interface\s+([A-Za-z_][A-Za-z0-9_]*)\s*{[^}]*}'
            matches = re.finditer(pattern, code, re.DOTALL)
            return self._process_regex_results(matches, code, context)
        except Exception as e:
            logger.debug(f'Regex extraction error: {e}')
            return []
    
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for TypeScript interfaces."""
        interfaces = []
        
        for node, capture_name in query_results:
            if capture_name == 'interface_def':
                # Extract interface name
                name_node = ast_handler.find_child_by_field_name(node, 'name')
                if name_node:
                    interface_name = ast_handler.get_node_text(name_node, code_bytes)
                    content = ast_handler.get_node_text(node, code_bytes)
                    
                    # Create interface info
                    interface_info = {
                        'type': 'interface',
                        'name': interface_name,
                        'content': content,
                        'range': {
                            'start': {'line': node.start_point[0] + 1, 'column': node.start_point[1]},
                            'end': {'line': node.end_point[0] + 1, 'column': node.end_point[1]}
                        }
                    }
                    
                    # Check if exported
                    export_parent = ast_handler.find_parent_of_type(node, 'export_statement')
                    if export_parent:
                        interface_info['is_exported'] = True
                        
                    interfaces.append(interface_info)
            elif capture_name == 'interface_name':
                interface_name = ast_handler.get_node_text(node, code_bytes)
                interface_node = ast_handler.find_parent_of_type(node, 'interface_declaration')
                if interface_node:
                    content = ast_handler.get_node_text(interface_node, code_bytes)
                    
                    # Create interface info
                    interface_info = {
                        'type': 'interface',
                        'name': interface_name,
                        'content': content,
                        'range': {
                            'start': {'line': interface_node.start_point[0] + 1, 'column': interface_node.start_point[1]},
                            'end': {'line': interface_node.end_point[0] + 1, 'column': interface_node.end_point[1]}
                        }
                    }
                    
                    # Check if exported
                    export_parent = ast_handler.find_parent_of_type(interface_node, 'export_statement')
                    if export_parent:
                        interface_info['is_exported'] = True
                        
                    interfaces.append(interface_info)
                    
        return interfaces
        
    def _process_regex_results(self, matches, code, context):
        """Process regex match results for interfaces."""
        interfaces = []
        
        for match in matches:
            if len(match.groups()) > 0:
                interface_name = match.group(1)
                content = match.group(0)
                
                # Extract line range
                start_pos = match.start()
                end_pos = match.end()
                start_line = code[:start_pos].count('\n') + 1
                end_line = code[:end_pos].count('\n') + 1
                
                # Create interface info
                interface_info = {
                    'type': 'interface',
                    'name': interface_name,
                    'content': content,
                    'range': {
                        'start': {'line': start_line, 'column': 0},
                        'end': {'line': end_line, 'column': 0}
                    }
                }
                
                # Check if exported
                prefix_text = code[:start_pos].strip().split('\n')[-1] if start_pos > 0 else ""
                if prefix_text.startswith('export '):
                    interface_info['is_exported'] = True
                    
                interfaces.append(interface_info)
                
        return interfaces