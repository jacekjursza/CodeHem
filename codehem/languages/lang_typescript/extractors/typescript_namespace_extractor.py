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
class TypeScriptNamespaceExtractor(TemplateExtractor):
    """ Extracts TypeScript namespace/module declarations. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.NAMESPACE

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Processes TreeSitter results for namespace/module declarations. """
        namespaces = []
        processed_node_ids = set()
        logger.debug(f'TS Namespace Extractor: Processing {len(query_results)} captures.')

        node_map: Dict[int, Dict[str, Any]] = {}

        for node, capture_name in query_results:
            definition_node = None
            node_for_range = node

            if capture_name in ['namespace_def', 'namespace_def_exported', 'ambient_namespace_def']:
                if node.type in ['module', 'namespace_declaration']: # TS uses both 'module' and 'namespace_declaration'
                    definition_node = node
                elif node.type in ['export_statement', 'ambient_declaration']:
                    decl = node.child_by_field_name('declaration')
                    if decl and decl.type in ['module', 'namespace_declaration']:
                        definition_node = decl
                    else: continue
                else:
                    logger.warning(f"Capture '{capture_name}' on unexpected node type: {node.type}")
                    continue
            elif capture_name in ['namespace_name', 'namespace_name_string', 'namespace_body']:
                 parent_def = ast_handler.find_parent_of_type(node, ['module', 'namespace_declaration'])
                 if parent_def:
                      definition_node = parent_def
                      # Check if exported or ambient for range
                      parent_outer = ast_handler.find_parent_of_type(definition_node, ['export_statement', 'ambient_declaration'])
                      if parent_outer and parent_outer.child_by_field_name('declaration') == definition_node:
                          node_for_range = parent_outer
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
                         if capture_name in ['namespace_name', 'namespace_name_string']:
                             node_map[node_id]['name_node'] = node # Prefer identifier if both exist
                             if capture_name == 'namespace_name_string' and 'name_node' not in node_map[node_id]:
                                node_map[node_id]['name_node'] = node # Use string if identifier missing
                         elif capture_name == 'namespace_body':
                              node_map[node_id]['body_node'] = node
                         # Update node_for_range if a larger context found
                         if node_for_range.start_byte < node_map[node_id]['node_for_range'].start_byte:
                              node_map[node_id]['node_for_range'] = node_for_range

        # Process collected info
        for node_id, data in node_map.items():
            if node_id in processed_node_ids: continue

            definition_node = data['definition_node']
            node_for_range = data['node_for_range']
            name_node = data.get('name_node')

            if not name_node:
                logger.warning(f"Could not find name for namespace/module definition node id {node_id}")
                processed_node_ids.add(node_id)
                continue

            namespace_name = ast_handler.get_node_text(name_node, code_bytes).strip('\'"') # Remove quotes if it was a string name
            content = ast_handler.get_node_text(node_for_range, code_bytes)
            start_point = node_for_range.start_point
            end_point = node_for_range.end_point

            decorators = ExtractorHelpers.extract_decorators(ast_handler, definition_node, code_bytes)

            namespace_info = {
                'type': CodeElementType.NAMESPACE.value,
                'name': namespace_name,
                'content': content,
                'range': {'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                          'end': {'line': end_point[0] + 1, 'column': end_point[1]}},
                'decorators': decorators,
                'node': definition_node
            }
            namespaces.append(namespace_info)
            processed_node_ids.add(node_id)
            logger.debug(f"TS Namespace Extractor: Processed namespace '{namespace_name}'")

        logger.debug(f'TS Namespace Extractor: Finished processing. Found {len(namespaces)} namespaces.')
        return namespaces

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        logger.warning("Regex fallback not implemented for TypeScriptNamespaceExtractor.")
        return []