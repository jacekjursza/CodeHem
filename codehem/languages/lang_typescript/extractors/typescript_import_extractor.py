import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.type_import import ImportExtractor # Use the base ImportExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry # Import registry to get config
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptImportExtractor(ImportExtractor):
    """ Extracts TypeScript/JavaScript import statements. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.IMPORT

    def __init__(self, language_code: str, language_type_descriptor: Optional[ElementTypeLanguageDescriptor]):
        super().__init__(language_code, language_type_descriptor)
        # Removed pattern loading from __init__ to avoid potential issues with config availability

    def _get_ts_query_from_config(self) -> Optional[str]:
        """ Helper to fetch the TS import query string directly from config. """
        try:
            lang_config = registry.get_language_config(self.language_code)
            if lang_config:
                placeholders = lang_config.get('template_placeholders', {}).get(self.ELEMENT_TYPE, {})
                if placeholders:
                    ts_query = placeholders.get('tree_sitter_query')
                    if ts_query:
                        logger.debug(f"Fetched TS import query from config: {ts_query}")
                        return ts_query
                    else:
                         logger.warning(f"TreeSitter query not found for {self.ELEMENT_TYPE} in TS config placeholders.")
                else:
                    logger.warning(f"No placeholders found for {self.ELEMENT_TYPE} in TS config.")
            else:
                logger.error("Could not retrieve TS language configuration from registry.")
        except Exception as e:
            logger.error(f"Error fetching TS import query from config: {e}", exc_info=True)
        return None

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """ Extract imports using TreeSitter for TypeScript/JavaScript. """
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            logger.error('TS ImportExtractor: ERROR - No AST handler available.')
            return []

        # --- Dynamically get the query string ---
        ts_query_string = self._get_ts_query_from_config()
        if not ts_query_string:
             logger.error("TS ImportExtractor: Could not get TreeSitter query string for imports.")
             return [] # Cannot proceed without a query
        # -----------------------------------------

        imports = []
        processed_node_ids = set()
        try:
            root, code_bytes = ast_handler.parse(code)
            logger.debug(f'TS ImportExtractor: Executing TS TreeSitter query: {repr(ts_query_string)}')
            query_results = ast_handler.execute_query(ts_query_string, root, code_bytes)
            logger.debug(f'TS ImportExtractor: TreeSitter query returned {len(query_results)} captures.')

            for node, capture_name in query_results:
                if node.id in processed_node_ids: continue

                # Check if the captured node is an import statement based on the query capture name
                if capture_name == 'import' and node.type == 'import_statement':
                    node_id = node.id
                    content = ast_handler.get_node_text(node, code_bytes)
                    name = 'import' # Default name, parse module name below
                    try:
                         # Attempt to find the module source string
                         source_node = node.child_by_field_name('source')
                         if source_node and source_node.type == 'string':
                              raw_module = ast_handler.get_node_text(source_node, code_bytes)
                              name = raw_module.strip('\'"') # Remove quotes
                         else:
                              # Fallback if source field isn't found directly (grammar might vary)
                              # Look for string literals within the node
                              for child in node.children:
                                   if child.type == 'string':
                                        raw_module = ast_handler.get_node_text(child, code_bytes)
                                        name = raw_module.strip('\'"')
                                        break
                    except Exception:
                        logger.warning(f"Could not parse module name from import: {content[:50]}...")

                    start_point = node.start_point
                    end_point = node.end_point
                    import_data = {
                        'type': CodeElementType.IMPORT.value,
                        'name': name,
                        'content': content,
                        'range': {
                            'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                            'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                        },
                        'node': node # Pass node for potential post-processing
                    }
                    imports.append(import_data)
                    processed_node_ids.add(node_id)
                    logger.debug(f"TS ImportExtractor: Extracted import: '{name}' at line {import_data['range']['start']['line']}")
                else:
                    logger.warning(f"TS ImportExtractor: Skipping capture '{capture_name}' with unexpected node type '{node.type}' for query '{ts_query_string}'")

        except QueryError as qe:
             logger.error(f'TS ImportExtractor: TreeSitter query failed: {qe}. Query: {ts_query_string}')
             # Optionally fallback to regex here if needed and implemented
             # return self._extract_with_regex(code, handler, context)
             return []
        except Exception as e:
            logger.error(f'TS ImportExtractor: Unexpected error during TreeSitter extraction: {e}', exc_info=True)
            return [] # Return empty list on error

        logger.debug(f'TS ImportExtractor: Finished TreeSitter processing, found {len(imports)} individual imports.')
        # Let the post-processor combine these
        return imports

    # _extract_with_regex can be implemented if robust regex fallback is needed
    # def _extract_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
    #     # ... implementation using handler.regexp_pattern ...
    #     return []