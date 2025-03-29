"""
Template implementation for property setter extractor.
"""
import logging
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
logger = logging.getLogger(__name__)

@extractor
class TemplatePropertySetterExtractor(TemplateExtractor):
    """Template implementation for property setter extraction."""
    ELEMENT_TYPE = CodeElementType.PROPERTY_SETTER

    def _process_tree_sitter_results(self, query_results, code_bytes, ast_handler, context):
        """Process tree-sitter query results for property setters.
        MODIFIED: Explicitly extracts decorators AND definition start location.
        """
        properties = []
        processed_nodes = set()

        for node, capture_name in query_results:
            if capture_name == 'property_setter_def':
                decorated_node = node
                if decorated_node.type != 'decorated_definition': continue

                definition_node = ast_handler.find_child_by_field_name(decorated_node, 'definition')
                if not definition_node or definition_node.type not in ['function_definition', 'method_definition']: continue
                if definition_node.id in processed_nodes: continue
                processed_nodes.add(definition_node.id)

                property_name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
                if not property_name_node: continue
                property_name = ast_handler.get_node_text(property_name_node, code_bytes)

                # --- Extract Decorators and verify setter ---
                decorators = []
                is_setter_decorator_present = False
                setter_prop_name = None

                for i in range(decorated_node.named_child_count):
                     child = decorated_node.named_child(i)
                     if child.type == 'decorator':
                          decorator_content = ast_handler.get_node_text(child, code_bytes)
                          decorator_name = None
                          # Check attribute type first (@name.setter)
                          if child.child_count > 0 and child.children[0].type == 'attribute':
                              attr_node = child.children[0]
                              obj_node = ast_handler.find_child_by_field_name(attr_node, 'object')
                              attribute_field = ast_handler.find_child_by_field_name(attr_node, 'attribute')
                              if obj_node and attribute_field:
                                  obj_name = ast_handler.get_node_text(obj_node, code_bytes)
                                  attr_name = ast_handler.get_node_text(attribute_field, code_bytes)
                                  decorator_name = f"{obj_name}.{attr_name}"
                                  if attr_name == 'setter':
                                      is_setter_decorator_present = True
                                      setter_prop_name = obj_name
                          # Check identifier type (@other)
                          elif child.child_count > 0 and child.children[0].type == 'identifier':
                               dec_name_node = child.children[0]
                               decorator_name = ast_handler.get_node_text(dec_name_node, code_bytes) if dec_name_node else None
                          # Fallback/More complex cases needed? @decorator() etc.

                          dec_range_data = {
                               'start': {'line': child.start_point[0] + 1, 'column': child.start_point[1]},
                               'end': {'line': child.end_point[0] + 1, 'column': child.end_point[1]}
                          }
                          decorators.append({
                               'name': decorator_name,
                               'content': decorator_content,
                               'range': dec_range_data
                          })
                # --------------------------------------------

                if not is_setter_decorator_present or setter_prop_name != property_name: continue

                # --- Extract Definition Location ---
                definition_start_line = definition_node.start_point[0] + 1
                definition_start_col = definition_node.start_point[1]
                # -------------------------------

                content = ast_handler.get_node_text(decorated_node, code_bytes)
                full_range_data = {
                    'start': {'line': decorated_node.start_point[0] + 1, 'column': decorated_node.start_point[1]},
                    'end': {'line': decorated_node.end_point[0] + 1, 'column': decorated_node.end_point[1]}
                }
                class_name = self._get_class_name(decorated_node, context, ast_handler, code_bytes)
                parameters = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes)
                return_info = ExtractorHelpers.extract_return_info(ast_handler, definition_node, code_bytes)

                property_info = {
                    'type': 'property_setter',
                    'name': property_name,
                    'content': content,
                    'class_name': class_name,
                    'range': full_range_data,
                    'decorators': decorators,
                    'parameters': parameters,
                    'return_info': return_info,
                    # Add definition location for deduplication
                    'definition_start_line': definition_start_line,
                    'definition_start_col': definition_start_col,
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