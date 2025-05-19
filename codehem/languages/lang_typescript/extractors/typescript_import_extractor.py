# -*- coding: utf-8 -*-
import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.type_import import ImportExtractor # Assuming this base exists
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry # Keep registry import if needed elsewhere
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptImportExtractor(ImportExtractor):
    """ Extracts TypeScript/JavaScript import statements using configured TreeSitter queries. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.IMPORT

    # No longer needed: def _get_ts_query_from_config(self) -> Optional[str]:

    def _extract_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """ Extract imports using TreeSitter for TypeScript/JavaScript. """
        ast_handler = self._get_ast_handler()
        if not ast_handler:
            logger.error('TS ImportExtractor: ERROR - No AST handler available.')
            return []

        if not handler or not handler.tree_sitter_query:
            logger.error(f'TS ImportExtractor: Missing TreeSitter query in handler for {self.ELEMENT_TYPE.value}.')
            return []

        ts_query_string = handler.tree_sitter_query
        imports = []
        processed_node_ids = set()
        try:
            root, code_bytes = ast_handler.parse(code)
            logger.debug(f'TS ImportExtractor: Executing TS TreeSitter query: {repr(ts_query_string)}')
            query_results = ast_handler.execute_query(ts_query_string, root, code_bytes)
            logger.debug(f'TS ImportExtractor: TreeSitter query returned {len(query_results)} captures.')

            for node, capture_name in query_results:
                # Process based on the primary import statement node captured
                # Assuming the query captures the whole import statement (e.g., @import)
                # Or potentially the export wrapper if it's an exported import
                import_statement_node = None
                node_for_range = node # Default to the captured node

                if node.type == 'import_statement':
                    import_statement_node = node
                elif node.type == 'export_statement':
                    # Look for an import_statement within the export declaration
                    decl = node.child_by_field_name('declaration')
                    if decl and decl.type == 'import_statement':
                        import_statement_node = decl
                        # Keep node_for_range as the export_statement
                    else: continue # Not an exported import
                elif node.type == 'import_clause':
                     # Find parent import_statement if only clause is captured
                     parent_import = ast_handler.find_parent_of_type(node, 'import_statement')
                     if parent_import:
                         import_statement_node = parent_import
                         node_for_range = parent_import # Use parent for range
                     else: continue
                else:
                    # If the capture is different, adjust logic or skip
                    logger.warning(f"TS ImportExtractor: Unexpected node type '{node.type}' captured as '{capture_name}'. Skipping.")
                    continue

                if import_statement_node and import_statement_node.id not in processed_node_ids:
                    node_id = import_statement_node.id
                    content = ast_handler.get_node_text(node_for_range, code_bytes) # Get text of the range node (might include export)
                    name = 'import' # Default name
                    try:
                        # Try to find the source module string
                        source_node = import_statement_node.child_by_field_name('source')
                        if source_node and source_node.type == 'string':
                            raw_module = ast_handler.get_node_text(source_node, code_bytes)
                            name = raw_module.strip('\'"')
                        else:
                            # Fallback search for any string literal within the import statement
                            for child in import_statement_node.children:
                                if child.type == 'string':
                                    raw_module = ast_handler.get_node_text(child, code_bytes)
                                    name = raw_module.strip('\'"')
                                    break
                    except Exception as e:
                        logger.warning(f"Could not parse module name from import: {content[:50]}... Error: {e}")

                    start_point = node_for_range.start_point
                    end_point = node_for_range.end_point
                    import_data = {
                        'type': CodeElementType.IMPORT.value,
                        'name': name, # Name is the module source
                        'content': content,
                        'range': {
                            'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                            'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                        },
                        'node': import_statement_node # Store the core import node
                    }
                    imports.append(import_data)
                    processed_node_ids.add(node_id)
                    # If range node was different (e.g., export), mark it processed too
                    if node_for_range.id != node_id:
                         processed_node_ids.add(node_for_range.id)

                    logger.debug(f"TS ImportExtractor: Extracted import: '{name}' at line {import_data['range']['start']['line']}")

        except QueryError as qe:
            logger.error(f'TS ImportExtractor: TreeSitter query failed: {qe}. Query: {ts_query_string}')
            return []
        except Exception as e:
            logger.error(f'TS ImportExtractor: Unexpected error during TreeSitter extraction: {e}', exc_info=True)
            return []

        logger.debug(f'TS ImportExtractor: Finished TreeSitter processing, found {len(imports)} individual imports.')
        # Let the post-processor handle combining imports if needed
        return imports

    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """ Extract imports using TreeSitter based on the provided handler's query. """
        return self._extract_with_tree_sitter(code, handler, context)
        # Regex fallback can be removed if TreeSitter is reliable
        # logger.warning("TS ImportExtractor: Regex fallback is currently disabled/not implemented.")
        # return []

    def _process_regex_results(self, matches, code, context) -> List[Dict]:
        # Implement or remove this if Regex fallback is needed/not needed
        logger.warning("TS ImportExtractor: Regex processing not implemented.")
        return []