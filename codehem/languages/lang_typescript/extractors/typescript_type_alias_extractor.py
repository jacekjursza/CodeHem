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
class TypeScriptTypeAliasExtractor(TemplateExtractor):
    """ Extracts TypeScript type alias declarations. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.TYPE_ALIAS

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Processes TreeSitter results for type alias declarations. """
        aliases = []
        processed_node_ids = set()
        logger.debug(f'TS Type Alias Extractor: Processing {len(query_results)} captures.')

        node_map: Dict[int, Dict[str, Any]] = {}

        for node, capture_name in query_results:
            definition_node = None
            node_for_range = node

            if capture_name in ['type_alias_def', 'type_alias_def_exported']:
                if node.type == 'type_alias_declaration':
                    definition_node = node
                elif node.type == 'export_statement':
                    decl = node.child_by_field_name('declaration')
                    if decl and decl.type == 'type_alias_declaration':
                        definition_node = decl
                    else: continue
                else:
                    logger.warning(f"Capture '{capture_name}' on unexpected node type: {node.type}")
                    continue
            elif capture_name in ['type_name', 'type_value']:
                 parent_def = ast_handler.find_parent_of_type(node, 'type_alias_declaration')
                 if parent_def:
                      definition_node = parent_def
                      # Check if parent is exported for range
                      parent_export = ast_handler.find_parent_of_type(definition_node, 'export_statement')
                      if parent_export and parent_export.child_by_field_name('declaration') == definition_node:
                          node_for_range = parent_export
                      else:
                           node_for_range = definition_node
                 else: continue

            if definition_node:
                node_id = definition_node.id
                if node_id not in processed_node_ids:
                    if node_id not in node_map:
                         node_map[node_id] = {'definition_node': definition_node, 'node_for_range': node_for_range}

                    # Store related nodes
                    if node_id in node_map:
                         if capture_name == 'type_name':
                             node_map[node_id]['name_node'] = node
                         elif capture_name == 'type_value':
                              node_map[node_id]['value_node'] = node
                         # Update node_for_range if a larger context found
                         if node_for_range.start_byte < node_map[node_id]['node_for_range'].start_byte:
                              node_map[node_id]['node_for_range'] = node_for_range

        # Process collected info
        for node_id, data in node_map.items():
            if node_id in processed_node_ids: continue

            definition_node = data['definition_node']
            node_for_range = data['node_for_range']
            name_node = data.get('name_node') or ast_handler.find_child_by_field_name(definition_node, 'name')
            value_node = data.get('value_node') or ast_handler.find_child_by_field_name(definition_node, 'value') # TS uses 'value' field

            if not name_node:
                logger.warning(f"Could not find name for type alias definition node id {node_id}")
                processed_node_ids.add(node_id)
                continue

            alias_name = ast_handler.get_node_text(name_node, code_bytes)
            alias_value = ast_handler.get_node_text(value_node, code_bytes) if value_node else None
            content = ast_handler.get_node_text(node_for_range, code_bytes)
            start_point = node_for_range.start_point
            end_point = node_for_range.end_point

            decorators = ExtractorHelpers.extract_decorators(ast_handler, definition_node, code_bytes) # Type aliases unlikely decorated

            alias_info = {
                'type': CodeElementType.TYPE_ALIAS.value,
                'name': alias_name,
                'content': content,
                'range': {'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                          'end': {'line': end_point[0] + 1, 'column': end_point[1]}},
                'value_type': alias_value, # Use value_type to store the aliased type string
                'decorators': decorators,
                'node': definition_node
            }
            aliases.append(alias_info)
            processed_node_ids.add(node_id)
            logger.debug(f"TS Type Alias Extractor: Processed alias '{alias_name}'")

        logger.debug(f'TS Type Alias Extractor: Finished processing. Found {len(aliases)} aliases.')
        return aliases

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        logger.warning("Regex fallback not implemented for TypeScriptTypeAliasExtractor.")
        return []