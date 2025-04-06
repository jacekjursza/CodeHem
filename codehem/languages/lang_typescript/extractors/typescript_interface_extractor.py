import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry
from codehem.core.engine.ast_handler import ASTHandler
# from codehem.core.extractors.extraction_base import ExtractorHelpers # If needed later

logger = logging.getLogger(__name__)

@extractor
class TypeScriptInterfaceExtractor(TemplateExtractor):
    """ Extracts TypeScript interface declarations. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.INTERFACE

    def __init__(self, language_code: str, language_type_descriptor: Optional[ElementTypeLanguageDescriptor]):
        super().__init__(language_code, language_type_descriptor)

    def _get_ts_query_from_config(self) -> Optional[str]:
        """ Helper to fetch the TS interface query string directly from config. """
        try:
            lang_config = registry.get_language_config(self.language_code)
            if lang_config:
                placeholders = lang_config.get('template_placeholders', {}).get(self.ELEMENT_TYPE, {})
                if placeholders:
                    ts_query = placeholders.get('tree_sitter_query')
                    if not ts_query:
                         # Fallback query based on TS grammar knowledge
                         ts_query = """
                         (interface_declaration
                           name: (type_identifier) @interface_name
                           body: (interface_body) @interface_body
                         ) @interface_def

                         (export_statement
                            declaration: (interface_declaration
                             name: (type_identifier) @interface_name
                             body: (interface_body) @interface_body
                           ) @interface_def_exported
                         )
                         """
                         logger.warning("Using fallback TS interface query string.")
                    logger.debug(f"Fetched TS interface query from config/fallback: {ts_query}")
                    return ts_query.strip()
                else:
                    logger.warning(f"No placeholders found for {self.ELEMENT_TYPE} in TS config.")
            else:
                logger.error("Could not retrieve TS language configuration from registry.")
        except Exception as e:
            logger.error(f"Error fetching TS interface query from config: {e}", exc_info=True)
        return None

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process tree-sitter query results for interfaces. """
        interfaces = []
        processed_node_ids = set()
        logger.debug(f"TS Interface Extractor: Processing {len(query_results)} captures.")

        for node, capture_name in query_results:
            interface_def_node = None
            interface_name = None
            node_for_range = node # Default node for range/content

            if capture_name in ["interface_def", "interface_def_exported"]:
                interface_def_node = node if capture_name == "interface_def" else node.child_by_field_name('declaration')
                if not interface_def_node or interface_def_node.type != 'interface_declaration': continue

                name_node = interface_def_node.child_by_field_name('name')
                if name_node:
                    interface_name = ast_handler.get_node_text(name_node, code_bytes)
                else:
                    logger.warning("Could not find name node for interface declaration.")
                    continue # Skip if no name

                if capture_name == "interface_def_exported": node_for_range = node

            # Less likely to capture only name, but handle defensively
            elif capture_name == "interface_name":
                 name_node = node
                 interface_name = ast_handler.get_node_text(name_node, code_bytes)
                 interface_def_node = ast_handler.find_parent_of_type(node, 'interface_declaration')
                 if not interface_def_node: continue

                 node_for_range = interface_def_node
                 export_stmt = ast_handler.find_parent_of_type(node_for_range, "export_statement")
                 if export_stmt: node_for_range = export_stmt

            if interface_def_node and interface_def_node.id not in processed_node_ids:
                try:
                    content = ast_handler.get_node_text(node_for_range, code_bytes)
                    start_point = node_for_range.start_point
                    end_point = node_for_range.end_point

                    # Interfaces typically don't have decorators in the same way classes do
                    decorators = []

                    # Extract members (properties, methods signatures) from the body?
                    # This might be better handled by the post-processor or dedicated property/method extractors
                    # For now, just extract the main interface declaration.
                    members_raw = []
                    body_node = interface_def_node.child_by_field_name('body')
                    # if body_node and body_node.type == 'interface_body':
                    #     # Process children like property_signature, method_signature etc.
                    #     pass # Add logic here if needed by post-processor

                    interface_info = {
                        'type': CodeElementType.INTERFACE.value,
                        'name': interface_name,
                        'content': content,
                        'range': {
                            'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                            'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                        },
                        'decorators': decorators,
                        'members_raw': members_raw, # Placeholder if body parsing is added
                        'node': interface_def_node
                    }
                    interfaces.append(interface_info)
                    processed_node_ids.add(interface_def_node.id)
                    logger.debug(f"TS Interface Extractor: Extracted interface '{interface_name}' at line {interface_info['range']['start']['line']}")
                except Exception as e:
                     logger.error(f"TS Interface Extractor: Error processing interface '{interface_name}': {e}", exc_info=True)

        logger.debug(f'TS Interface Extractor: Finished TreeSitter processing, found {len(interfaces)} interfaces.')
        return interfaces

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """ Extracts interfaces using TreeSitter. """
        if not handler:
             logger.error("TS Interface Extractor: Missing language type descriptor.")
             return []

        ts_query_string = self._get_ts_query_from_config()
        if not ts_query_string:
            logger.error("TS Interface Extractor: Could not get TreeSitter query string.")
            return []

        elements = []
        ast_handler = self._get_ast_handler()
        if ast_handler:
             try:
                 root, code_bytes = ast_handler.parse(code)
                 query_results = ast_handler.execute_query(ts_query_string, root, code_bytes)
                 elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
             except QueryError as qe:
                 logger.error(f'TS Interface Extractor: TreeSitter query failed: {qe}. Query: {ts_query_string}')
             except Exception as e:
                 logger.error(f'TS Interface Extractor: Error during TreeSitter extraction: {e}', exc_info=True)
        else:
             logger.warning("TS Interface Extractor: Skipping TreeSitter extraction (no handler).")

        # Regex fallback unlikely to be robust for interfaces, skipping for now

        return elements

    # Regex fallback not implemented
    # def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
    #     return []