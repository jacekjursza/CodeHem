"""
TypeScript-specific method extractor implementation.
"""
import logging
from typing import Dict, List, Any
from codehem.extractors.template_method_extractor import TemplateMethodExtractor
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor

logger = logging.getLogger(__name__)

@extractor
class TypeScriptMethodExtractor(TemplateMethodExtractor):
    """TypeScript-specific implementation for method extraction."""
    LANGUAGE_CODE = 'typescript'
    
    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results with TypeScript-specific handling."""
        methods = super()._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
        
        # For TypeScript, extract access modifiers and additional info
        for method_info in methods:
            try:
                # Find the method node
                method_node = next((node for node, capture_name in query_results 
                                if capture_name == 'method_def' and 
                                ast_handler.get_node_text(node, code_bytes).find(method_info['name']) != -1), None)
                
                if method_node:
                    # Check for access modifiers
                    modifiers = []
                    for i in range(method_node.named_child_count):
                        child = method_node.named_child(i)
                        if child.type in ['public', 'private', 'protected']:
                            modifiers.append(ast_handler.get_node_text(child, code_bytes))
                    
                    if modifiers:
                        method_info['modifiers'] = modifiers
                        
                    # Check for async
                    if 'async ' in ast_handler.get_node_text(method_node, code_bytes).split('(')[0]:
                        method_info['is_async'] = True
            except Exception as e:
                logger.debug(f"Error extracting TypeScript method details: {e}")
                
        return methods