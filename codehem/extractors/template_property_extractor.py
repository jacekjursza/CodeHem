"""
Template implementation for property extractor.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from codehem.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplatePropertyExtractor(TemplateExtractor):
    """Template implementation for property extraction."""
    ELEMENT_TYPE = CodeElementType.PROPERTY

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for properties."""
        properties = []
        for node, capture_name in query_results:
            if capture_name == 'property_def':
                # Extract property name and value
                name_node = ast_handler.find_child_by_field_name(node, 'name')
                if name_node:
                    property_name = ast_handler.get_node_text(name_node, code_bytes)
                    content = ast_handler.get_node_text(node, code_bytes)
                    
                    # Determine parent class
                    class_name = self._get_class_name(node, context, ast_handler, code_bytes)
                    
                    # Get property value type if possible
                    value_type = self._extract_property_type(node, code_bytes, ast_handler)
                    
                    # Create property info
                    property_info = {
                        'type': 'property',
                        'name': property_name,
                        'content': content,
                        'class_name': class_name,
                        'range': {
                            'start': {'line': node.start_point[0] + 1, 'column': node.start_point[1]},
                            'end': {'line': node.end_point[0] + 1, 'column': node.end_point[1]}
                        },
                        'value_type': value_type
                    }
                    properties.append(property_info)
                    
        return properties

    def _get_class_name(self, node, context, ast_handler, code_bytes):
        """Get class name for a property node."""
        class_name = None
        if context and 'class_name' in context:
            class_name = context['class_name']
        else:
            class_node = ast_handler.find_parent_of_type(node, 'class_definition')
            if not class_node:
                class_node = ast_handler.find_parent_of_type(node, 'class_declaration')
            if class_node:
                class_name_node = ast_handler.find_child_by_field_name(class_node, 'name')
                if class_name_node:
                    class_name = ast_handler.get_node_text(class_name_node, code_bytes)
        return class_name

    def _extract_property_type(self, node, code_bytes, ast_handler):
        """Extract property type if available."""
        # This will be language-specific, so provide a default implementation
        return None

    def _process_regex_results(self, matches, code, context):
        """Process regex match results for properties."""
        properties = []
        class_name = context.get('class_name')
        
        for match in matches:
            prop_name = match.group(1) if len(match.groups()) > 0 else "unknown"
            content = match.group(0)
            
            # Extract line range
            start_pos = match.start()
            end_pos = match.end()
            start_line = code[:start_pos].count('\n') + 1
            end_line = code[:end_pos].count('\n') + 1
            
            # Create property info
            property_info = {
                'type': 'property',
                'name': prop_name,
                'content': content,
                'class_name': class_name,
                'range': {
                    'start': {'line': start_line, 'column': 0},
                    'end': {'line': end_line, 'column': 0}
                },
                'value_type': None  # Regex often can't reliably determine types
            }
            properties.append(property_info)
            
        return properties