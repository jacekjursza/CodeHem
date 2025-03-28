"""
Template implementation for property setter extractor.
"""
import logging
import re
from typing import Dict, List, Optional, Any
from codehem.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplatePropertySetterExtractor(TemplateExtractor):
    """Template implementation for property setter extraction."""
    ELEMENT_TYPE = CodeElementType.PROPERTY_SETTER

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for property setters."""
        properties = []
        for node, capture_name in query_results:
            if capture_name == 'property_setter_def':
                # Handle decorated property setter definitions
                property_name = None
                definition_node = None
                
                if node.type == 'decorated_definition':
                    # Find the property.setter decorator and method name
                    decorator_found = False
                    for i in range(node.named_child_count):
                        child = node.named_child(i)
                        if child.type == 'decorator':
                            # Look for property_name.setter pattern
                            decorator_node = ast_handler.find_child_by_field_name(child, 'name')
                            if decorator_node:
                                decorator_text = ast_handler.get_node_text(decorator_node, code_bytes)
                                if '.' in decorator_text and decorator_text.endswith('.setter'):
                                    decorator_found = True
                                    prop_obj = decorator_text.split('.')[0]
                                    
                        elif child.type == 'function_definition' or child.type == 'method_definition':
                            definition_node = child
                            name_node = ast_handler.find_child_by_field_name(child, 'name')
                            if name_node:
                                property_name = ast_handler.get_node_text(name_node, code_bytes)
                                
                    if not decorator_found or not property_name:
                        continue
                else:
                    continue
                
                if property_name and definition_node:
                    # Get content and class name
                    content = ast_handler.get_node_text(node, code_bytes)
                    class_name = self._get_class_name(node, context, ast_handler, code_bytes)
                    
                    # Extract parameters
                    parameters = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes)
                    
                    # Create property setter info
                    property_info = {
                        'type': 'property_setter',
                        'name': property_name,
                        'content': content,
                        'class_name': class_name,
                        'range': {
                            'start': {'line': node.start_point[0] + 1, 'column': node.start_point[1]},
                            'end': {'line': node.end_point[0] + 1, 'column': node.end_point[1]}
                        },
                        'parameters': parameters
                    }
                    properties.append(property_info)
                    
        return properties

    def _get_class_name(self, node, context, ast_handler, code_bytes):
        """Get class name for a property setter node."""
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

    def _process_regex_results(self, matches, code, context):
        """Process regex match results for property setters."""
        properties = []
        class_name = context.get('class_name')
        
        for match in matches:
            if len(match.groups()) > 1:
                prop_obj = match.group(1)  # Property name from decorator
                property_name = match.group(2)  # Method name
                content = match.group(0)
                
                # Extract line range
                start_pos = match.start()
                end_pos = match.end()
                start_line = code[:start_pos].count('\n') + 1
                end_line = code[:end_pos].count('\n') + 1
                
                # Create property setter info
                property_info = {
                    'type': 'property_setter',
                    'name': property_name,
                    'content': content,
                    'class_name': class_name,
                    'range': {
                        'start': {'line': start_line, 'column': 0},
                        'end': {'line': end_line, 'column': 0}
                    },
                    'parameters': []
                }
                properties.append(property_info)
                
        return properties