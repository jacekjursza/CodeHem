import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptPropertyExtractor(TemplateExtractor):
    """ Extracts TypeScript/JavaScript properties (class fields). """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.PROPERTY

    def _get_parent_class_name(self, node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[str]:
        """ Finds the name of the containing class or interface definition """
        container_node_types = ['class_declaration', 'interface_declaration', 'object_type']
        current_node = node.parent
        while current_node:
            if current_node.type in container_node_types:
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node and name_node.type in ['type_identifier', 'identifier']:
                    return ast_handler.get_node_text(name_node, code_bytes)
                return f"Container_{current_node.type}" # Placeholder
            if current_node.type == 'program': break
            current_node = current_node.parent
        return None

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Processes TreeSitter results for property definitions. """
        properties = []
        processed_node_ids = set()
        logger.debug(f'TS Property Extractor: Processing {len(query_results)} captures.')

        node_map: Dict[int, Dict[str, Any]] = {}

        # Collect info based on the definition node ID
        for node, capture_name in query_results:
            definition_node = None
            # Identify the core definition node ('public_field_definition', 'property_signature')
            if capture_name == 'property_def':
                 # The captured node IS the definition node
                 if node.type in ['public_field_definition', 'property_signature']:
                      definition_node = node
                 else:
                     # Handle cases where property_def might capture a parent like export_statement
                     if node.type == 'export_statement':
                         decl = node.child_by_field_name('declaration')
                         if decl and decl.type == 'public_field_definition':
                             definition_node = decl
                         else: continue
                     else:
                         logger.warning(f"Capture 'property_def' on unexpected node type: {node.type}")
                         continue

            elif capture_name in ['property_name', 'type', 'value']:
                # Find the parent definition node
                parent_def = ast_handler.find_parent_of_type(node, ['public_field_definition', 'property_signature'])
                if parent_def:
                     definition_node = parent_def
                else:
                    # Check if it's part of an export statement's definition
                    parent_export = ast_handler.find_parent_of_type(node, 'export_statement')
                    if parent_export:
                        decl = parent_export.child_by_field_name('declaration')
                        if decl and decl.type == 'public_field_definition':
                           parent_def_check = ast_handler.find_parent_of_type(node, 'public_field_definition')
                           if parent_def_check == decl:
                               definition_node = decl
                           else: continue
                        else: continue
                    else: continue # Skip if not part of a valid definition

            if definition_node:
                node_id = definition_node.id
                if node_id not in processed_node_ids:
                     if node_id not in node_map:
                         # Ensure it's inside a class/interface before proceeding
                         class_name = self._get_parent_class_name(definition_node, ast_handler, code_bytes)
                         if class_name:
                              node_map[node_id] = {'definition_node': definition_node, 'class_name': class_name, 'node_for_range': definition_node}
                              # If definition node is inside export, use export for range
                              parent_export = ast_handler.find_parent_of_type(definition_node, 'export_statement')
                              if parent_export and parent_export.child_by_field_name('declaration') == definition_node:
                                  node_map[node_id]['node_for_range'] = parent_export
                         else:
                              processed_node_ids.add(node_id) # Skip if not in class/interface
                              continue

                     # Store related nodes
                     if node_id in node_map:
                          if capture_name == 'property_name':
                              node_map[node_id]['name_node'] = node
                          elif capture_name == 'type':
                              node_map[node_id]['type_node'] = node
                          elif capture_name == 'value':
                              node_map[node_id]['value_node'] = node

        # Process the collected information
        for node_id, data in node_map.items():
            if node_id in processed_node_ids: continue

            definition_node = data['definition_node']
            class_name = data['class_name']
            node_for_range = data['node_for_range']

            name_node = data.get('name_node') or ast_handler.find_child_by_field_name(definition_node, 'name')
            type_node = data.get('type_node') or ast_handler.find_child_by_field_name(definition_node, 'type')
            value_node = data.get('value_node') or ast_handler.find_child_by_field_name(definition_node, 'value')

            if not name_node:
                logger.warning(f"Could not find name node for property definition node id {node_id}")
                processed_node_ids.add(node_id)
                continue

            prop_name = ast_handler.get_node_text(name_node, code_bytes)
            prop_type = ast_handler.get_node_text(type_node, code_bytes) if type_node else None
            prop_value = ast_handler.get_node_text(value_node, code_bytes) if value_node else None
            content = ast_handler.get_node_text(node_for_range, code_bytes)

            # Clean up type if it includes the colon
            if prop_type and isinstance(prop_type, str) and prop_type.startswith(':'):
                 prop_type = prop_type[1:].strip()

            start_point = node_for_range.start_point
            end_point = node_for_range.end_point

            # Use ExtractorHelpers for decorators
            decorators = ExtractorHelpers.extract_decorators(ast_handler, definition_node, code_bytes)

            prop_info = {
                'type': CodeElementType.PROPERTY.value,
                'name': prop_name,
                'content': content,
                'class_name': class_name,
                'range': {'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                          'end': {'line': end_point[0] + 1, 'column': end_point[1]}},
                'value_type': prop_type,
                'additional_data': {'value': prop_value} if prop_value else {},
                'decorators': decorators,
                'node': definition_node # Keep node for potential further processing
            }
            properties.append(prop_info)
            processed_node_ids.add(node_id)
            logger.debug(f"TS Property Extractor: Processed '{class_name}.{prop_name}'")

        logger.debug(f'TS Property Extractor: Finished processing. Found {len(properties)} properties.')
        return properties

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """ Regex fallback for properties. """
        logger.warning("Regex fallback used for TypeScriptPropertyExtractor.")
        # Basic regex might be too unreliable for TS properties due to complexity.
        # Returning empty list for now, assuming TreeSitter is preferred.
        return []