# -*- coding: utf-8 -*-
import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry # Keep registry import if needed elsewhere
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptInterfaceExtractor(TemplateExtractor):
    """ Extracts TypeScript interface declarations using configured TreeSitter queries. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.INTERFACE

    # No longer needed: def _get_ts_query_from_config(self) -> Optional[str]:

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process tree-sitter query results for interfaces. """
        interfaces = []
        processed_node_ids = set()
        node_map = {}
        logger.debug(f"TS Interface Extractor: Processing {len(query_results)} raw captures.") # ADDED LOG

        # Build node_map (existing logic)
        for node, capture_name in query_results:
            current_def_node = None
            node_for_range = None
            if capture_name in ['interface_def', 'interface_def_exported']:
                node_for_range = node
                current_def_node = node if node.type == 'interface_declaration' else node.child_by_field_name('declaration')
            elif capture_name in ['interface_name', 'type_parameters', 'interface_body']:
                parent_decl = ast_handler.find_parent_of_type(node, 'interface_declaration')
                if parent_decl:
                    current_def_node = parent_decl
                    export_parent = ast_handler.find_parent_of_type(parent_decl, 'export_statement')
                    node_for_range = export_parent or parent_decl
            if current_def_node and node_for_range:
                node_id = current_def_node.id
                if node_id not in node_map:
                    node_map[node_id] = {'node': current_def_node, 'range_node': node_for_range}
                if node_for_range.start_byte < node_map[node_id]['range_node'].start_byte:
                    node_map[node_id]['range_node'] = node_for_range
                if capture_name == 'interface_name':
                    node_map[node_id]['name_node'] = node
                elif capture_name == 'type_parameters':
                    node_map[node_id]['type_parameters_node'] = node

        logger.debug(f"TS Interface Extractor: Built node map with {len(node_map)} potential interfaces.") # ADDED LOG

        # Process node_map (existing logic)
        for node_id, parts in node_map.items():
            if node_id in processed_node_ids:
                continue
            interface_decl_node = parts.get('node')
            node_for_range = parts.get('range_node')

            if not interface_decl_node or interface_decl_node.type != 'interface_declaration':
                logger.warning(f"TS Interface Extractor: Skipping node_id {node_id}, not a valid interface_declaration.") # ADDED LOG
                continue

            name_node = parts.get('name_node') or ast_handler.find_child_by_field_name(interface_decl_node, 'name')
            interface_name = ast_handler.get_node_text(name_node, code_bytes) if name_node else None

            if not interface_name:
                logger.warning(f'TS Interface Extractor: Could not find name node for interface definition node id {node_id}')
                continue

            logger.debug(f"TS Interface Extractor: Processing interface '{interface_name}' (Node ID: {node_id})") # ADDED LOG
            try:
                content = ast_handler.get_node_text(node_for_range, code_bytes)
                start_point = node_for_range.start_point
                end_point = node_for_range.end_point
                decorators = [] # Assuming interfaces don't have decorators captured this way yet
                interface_info = {
                    'type': CodeElementType.INTERFACE.value,
                    'name': interface_name,
                    'content': content,
                    'range': {
                        'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                        'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                    },
                    'decorators': decorators,
                    'node': interface_decl_node # Keep node temporarily for post-processor if needed
                }
                interfaces.append(interface_info)
                processed_node_ids.add(node_id)
                logger.debug(f"TS Interface Extractor: Successfully extracted raw data for interface '{interface_name}' at line {interface_info['range']['start']['line']}")
            except Exception as e:
                logger.error(f"TS Interface Extractor: Error processing interface '{interface_name}' (node id {node_id}): {e}", exc_info=True)

        logger.debug(f'TS Interface Extractor: Finished TreeSitter processing, returning {len(interfaces)} raw interface dicts.')
        return interfaces

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """ Extracts interfaces using TreeSitter based on the provided handler's query. """
        if not handler or not handler.tree_sitter_query:
            logger.error(f'TS Interface Extractor: Missing language type descriptor or TreeSitter query for {self.ELEMENT_TYPE.value}.')
            return []

        logger.debug(f"TS Interface Extractor: Starting extraction with pattern. Context: {context}") # ADDED LOG
        elements = []
        ast_handler = self._get_ast_handler()
        if ast_handler:
            try:
                logger.debug(f'TS Interface Extractor: Using TreeSitter query from handler: {repr(handler.tree_sitter_query)}') # MODIFIED LOG LEVEL
                root, code_bytes = ast_handler.parse(code)
                query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
                logger.debug(f"TS Interface Extractor: Raw query results count: {len(query_results)}") # ADDED LOG
                elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
            except QueryError as qe:
                logger.error(f'TS Interface Extractor: TreeSitter query failed: {qe}. Query: {handler.tree_sitter_query}')
            except Exception as e:
                logger.error(f'TS Interface Extractor: Error during TreeSitter extraction: {e}', exc_info=True)
        else:
            logger.warning('TS Interface Extractor: AST handler not available, skipping TreeSitter extraction.')

        logger.debug(f"TS Interface Extractor: Finished extraction with pattern. Found {len(elements)} raw interface elements.") # ADDED LOG
        return elements

    def _process_regex_results(self, matches, code, context) -> List[Dict]:
        # Implement or remove this if Regex fallback is needed/not needed
        logger.warning("TS Interface Extractor: Regex processing not implemented.")
        return []