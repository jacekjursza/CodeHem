"""
Template implementation for property getter extractor.
"""
import logging
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplatePropertyGetterExtractor(TemplateExtractor):
    """Template implementation for property getter extraction."""
    ELEMENT_TYPE = CodeElementType.PROPERTY_GETTER

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for property getters.
        MODIFIED: Explicitly extracts decorators AND definition start location.
        """
        properties = []
        processed_nodes = set()

        for node, capture_name in query_results:
            if capture_name == 'property_def':
                decorated_node = node
                if decorated_node.type != 'decorated_definition':
                    if node.type == 'function_definition' and node.parent and (node.parent.type == 'decorated_definition'):
                        decorated_node = node.parent
                    else:
                        continue

                definition_node = ast_handler.find_child_by_field_name(decorated_node, 'definition')
                if not definition_node or definition_node.type not in ['function_definition', 'method_definition']:
                    continue

                if definition_node.id in processed_nodes:
                    continue

                processed_nodes.add(definition_node.id)
                property_name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
                if not property_name_node:
                    continue

                property_name = ast_handler.get_node_text(property_name_node, code_bytes)
                decorators = []
                is_getter_decorator_present = False

                for i in range(decorated_node.named_child_count):
                    child = decorated_node.named_child(i)
                    if child.type == 'decorator':
                        decorator_content = ast_handler.get_node_text(child, code_bytes)
                        dec_name_node = ast_handler.find_child_by_field_name(child, 'name')
                        decorator_name = ast_handler.get_node_text(dec_name_node, code_bytes) if dec_name_node else None

                        if not decorator_name:
                            if child.child_count > 0 and child.children[0].type == 'identifier':
                                decorator_name = ast_handler.get_node_text(child.children[0], code_bytes)

                        if decorator_name == 'property':
                            is_getter_decorator_present = True

                        dec_range_data = {'start': {'line': child.start_point[0] + 1, 'column': child.start_point[1]}, 
                                         'end': {'line': child.end_point[0] + 1, 'column': child.end_point[1]}}

                        decorators.append({
                            'name': decorator_name, 
                            'content': decorator_content, 
                            'range': dec_range_data
                        })

                if not is_getter_decorator_present:
                    continue

                definition_start_line = definition_node.start_point[0] + 1
                definition_start_col = definition_node.start_point[1]
                content = ast_handler.get_node_text(decorated_node, code_bytes)
                full_range_data = {'start': {'line': decorated_node.start_point[0] + 1, 'column': decorated_node.start_point[1]}, 
                                  'end': {'line': decorated_node.end_point[0] + 1, 'column': decorated_node.end_point[1]}}
                class_name = self._get_class_name(decorated_node, context, ast_handler, code_bytes)
                parameters = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes)
                return_info = ExtractorHelpers.extract_return_info(ast_handler, definition_node, code_bytes)

                property_info = {
                    'type': 'property_getter', 
                    'name': property_name, 
                    'content': content, 
                    'class_name': class_name, 
                    'range': full_range_data, 
                    'decorators': decorators, 
                    'parameters': parameters, 
                    'return_info': return_info, 
                    'definition_start_line': definition_start_line, 
                    'definition_start_col': definition_start_col,
                    'has_property_decorator': True  # Flag to indicate this is a true property
                }
                properties.append(property_info)

        return properties

    def _get_class_name(self, node, context, ast_handler, code_bytes):
        """Get class name for a property getter node."""
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
        """Process regex match results for property getters."""
        properties = []
        class_name = context.get('class_name')
        
        for match in matches:
            if len(match.groups()) > 0:
                property_name = match.group(1)
                content = match.group(0)
                
                # Extract line range
                start_pos = match.start()
                end_pos = match.end()
                start_line = code[:start_pos].count('\n') + 1
                end_line = code[:end_pos].count('\n') + 1
                
                # Create property getter info
                property_info = {
                    'type': 'property_getter',
                    'name': property_name,
                    'content': content,
                    'class_name': class_name,
                    'range': {
                        'start': {'line': start_line, 'column': 0},
                        'end': {'line': end_line, 'column': 0}
                    },
                    'return_info': {'return_type': None, 'return_values': []},
                    'parameters': []
                }
                properties.append(property_info)
                
        return properties