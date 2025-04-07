# -*- coding: utf-8 -*-
import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry # Keep registry import if needed elsewhere
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptClassExtractor(TemplateExtractor):
    """ Extracts TypeScript/JavaScript class declarations using configured TreeSitter queries. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.CLASS

    # No longer needed: def _get_ts_query_from_config(self) -> Optional[str]:

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process tree-sitter query results for classes based on configured query captures. """
        classes = []
        processed_node_ids = set()
        logger.debug(f'TS Class Extractor: Processing {len(query_results)} captures.')

        # Simplified logic: iterate captures, identify main definition node, extract info
        node_map = {} # Store parts related to a potential class definition node ID
        for node, capture_name in query_results:
            # Try to find the primary node representing the class definition
            current_def_node = None
            if capture_name in ['class_def', 'class_def_exported', 'abstract_class_def']: # Add other top-level captures if needed
                current_def_node = node
            elif capture_name in ['class_name']:
                 # Find the containing class_declaration or export_statement/declaration
                 parent_decl = ast_handler.find_parent_of_type(node, ['class_declaration', 'abstract_class_declaration'])
                 if parent_decl:
                     export_parent = ast_handler.find_parent_of_type(parent_decl, 'export_statement')
                     current_def_node = export_parent or parent_decl # Use export statement for range if present
                 else:
                     continue # Name found outside expected structure
            elif capture_name in ['class_body']:
                 parent_decl = ast_handler.find_parent_of_type(node, ['class_declaration', 'abstract_class_declaration'])
                 if parent_decl:
                     export_parent = ast_handler.find_parent_of_type(parent_decl, 'export_statement')
                     current_def_node = export_parent or parent_decl
                 else:
                     continue # Body found outside expected structure
            else:
                # Skip captures not directly defining or naming the class
                continue

            if current_def_node:
                node_id = current_def_node.id
                if node_id not in node_map:
                    node_map[node_id] = {'node': current_def_node} # Store the node used for range/content
                # Add specific parts if captured separately
                if capture_name == 'class_name':
                    node_map[node_id]['name_node'] = node
                if capture_name == 'class_body':
                    node_map[node_id]['body_node'] = node

        # Process the assembled node information
        for node_id, parts in node_map.items():
            if node_id in processed_node_ids:
                continue

            node_for_range = parts.get('node')
            # Extract the core class declaration node if nested inside export etc.
            class_decl_node = node_for_range
            if node_for_range.type == 'export_statement':
                 decl = node_for_range.child_by_field_name('declaration')
                 if decl and decl.type in ['class_declaration', 'abstract_class_declaration']:
                     class_decl_node = decl
                 else: continue # Malformed export

            if not class_decl_node or class_decl_node.type not in ['class_declaration', 'abstract_class_declaration']:
                continue # Skip if not a class node

            # Prefer captured name node, fallback to finding it
            name_node = parts.get('name_node') or ast_handler.find_child_by_field_name(class_decl_node, 'name')
            class_name = ast_handler.get_node_text(name_node, code_bytes) if name_node else None

            if not class_name:
                logger.warning(f'Could not find name node for class definition node id {node_id}')
                continue

            try:
                content = ast_handler.get_node_text(node_for_range, code_bytes)
                start_point = node_for_range.start_point
                end_point = node_for_range.end_point
                # Decorators need a robust extraction method, potentially querying the AST above node_for_range
                decorators = [] # Placeholder - implement decorator extraction if needed
                class_info = {
                    'type': CodeElementType.CLASS.value,
                    'name': class_name,
                    'content': content,
                    'range': {
                        'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                        'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                    },
                    'decorators': decorators,
                    'node': class_decl_node # Store the actual class declaration node
                }
                classes.append(class_info)
                processed_node_ids.add(node_id)
                # Add ID of the core class node too if different from the range node
                if class_decl_node.id != node_id:
                    processed_node_ids.add(class_decl_node.id)

                logger.debug(f"TS Class Extractor: Extracted class '{class_name}' at line {class_info['range']['start']['line']}")
            except Exception as e:
                logger.error(f"TS Class Extractor: Error processing class '{class_name}' (node id {node_id}): {e}", exc_info=True)

        logger.debug(f'TS Class Extractor: Finished TreeSitter processing, found {len(classes)} classes.')
        return classes

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """ Extracts classes using TreeSitter based on the provided handler's query. """
        if not handler or not handler.tree_sitter_query:
            logger.error(f'TS Class Extractor: Missing language type descriptor or TreeSitter query for {self.ELEMENT_TYPE.value}.')
            return []

        elements = []
        ast_handler = self._get_ast_handler()
        if ast_handler:
            try:
                logger.debug(f"TS Class Extractor: Using TreeSitter query from handler: {handler.tree_sitter_query}")
                root, code_bytes = ast_handler.parse(code)
                query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
                elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
            except QueryError as qe:
                logger.error(f'TS Class Extractor: TreeSitter query failed: {qe}. Query: {handler.tree_sitter_query}')
            except Exception as e:
                logger.error(f'TS Class Extractor: Error during TreeSitter extraction: {e}', exc_info=True)
        else:
            logger.warning('TS Class Extractor: AST handler not available, skipping TreeSitter extraction.')

        # Remove or simplify Regex fallback if TreeSitter is reliable
        # if not elements and handler.regexp_pattern:
        #    logger.warning('TS Class Extractor: Regex fallback is currently disabled/not implemented.')
            # elements = self._process_regex_results(...)

        return elements

    def _process_regex_results(self, matches, code, context) -> List[Dict]:
        # Implement or remove this if Regex fallback is needed/not needed
        logger.warning("TS Class Extractor: Regex processing not implemented.")
        return []