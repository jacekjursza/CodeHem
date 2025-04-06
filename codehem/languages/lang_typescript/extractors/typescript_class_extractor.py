import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptClassExtractor(TemplateExtractor):
    """ Extracts TypeScript/JavaScript class declarations. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.CLASS

    def __init__(self, language_code: str, language_type_descriptor: Optional[ElementTypeLanguageDescriptor]):
        super().__init__(language_code, language_type_descriptor)
        # Patterns will be fetched dynamically if needed

    def _get_ts_query_from_config(self) -> Optional[str]:
        """ Helper to fetch the TS class query string directly from config. """
        try:
            lang_config = registry.get_language_config(self.language_code)
            if lang_config:
                placeholders = lang_config.get('template_placeholders', {}).get(self.ELEMENT_TYPE, {})
                if placeholders:
                    # Need a specific TreeSitter query for classes in TS
                    # Example based on common patterns, might need refinement from config
                    ts_query = placeholders.get('tree_sitter_query')
                    if not ts_query: # Fallback if not in config yet
                        ts_query = """
                        (class_declaration
                          name: (type_identifier) @class_name
                          body: (class_body) @class_body
                        ) @class_def

                        (export_statement
                          declaration: (class_declaration
                            name: (type_identifier) @class_name
                            body: (class_body) @class_body
                          ) @class_def_exported
                        )
                        """
                        logger.warning("Using fallback TS class query string.")
                    logger.debug(f"Fetched TS class query from config/fallback: {ts_query}")
                    return ts_query.strip()
                else:
                    logger.warning(f"No placeholders found for {self.ELEMENT_TYPE} in TS config.")
            else:
                logger.error("Could not retrieve TS language configuration from registry.")
        except Exception as e:
            logger.error(f"Error fetching TS class query from config: {e}", exc_info=True)
        return None

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process tree-sitter query results for classes. """
        classes = []
        processed_node_ids = set()
        logger.debug(f"TS Class Extractor: Processing {len(query_results)} captures.")

        for node, capture_name in query_results:
            class_def_node = None
            class_name = None
            class_name_node = None
            class_body_node = None

            # Identify the main class definition node and relevant parts
            if capture_name in ["class_def", "class_def_exported"]:
                class_def_node = node
                class_name_node = ast_handler.find_child_by_field_name(class_def_node, 'name')
                class_body_node = ast_handler.find_child_by_field_name(class_def_node, 'body')
                if class_name_node:
                    class_name = ast_handler.get_node_text(class_name_node, code_bytes)
                else:
                     logger.warning(f"Could not find name node for class definition: {ast_handler.get_node_text(class_def_node, code_bytes)[:100]}...")
                     continue # Skip if no name found
                # Need the outer node (potentially export_statement) for full range/content
                if capture_name == "class_def_exported":
                     export_stmt_node = ast_handler.find_parent_of_type(node, "export_statement")
                     if export_stmt_node:
                          node_for_range = export_stmt_node
                     else:
                          node_for_range = class_def_node # Fallback
                else:
                    node_for_range = class_def_node

            # Alternative capture for just the name (less preferred but useful as fallback)
            elif capture_name == "class_name":
                class_name_node = node
                class_name = ast_handler.get_node_text(class_name_node, code_bytes)
                # Find the parent class definition node
                class_def_node = ast_handler.find_parent_of_type(class_name_node, 'class_declaration')
                if not class_def_node:
                    logger.debug(f"Class name '{class_name}' captured but couldn't find parent class_declaration.")
                    continue # Skip if we only got the name without the definition node

                node_for_range = class_def_node
                export_stmt_node = ast_handler.find_parent_of_type(class_def_node, "export_statement")
                if export_stmt_node:
                      node_for_range = export_stmt_node

            if class_def_node and class_def_node.id not in processed_node_ids:
                try:
                    content = ast_handler.get_node_text(node_for_range, code_bytes)
                    start_point = node_for_range.start_point
                    end_point = node_for_range.end_point

                    # Extract decorators associated with the class (might be on export_statement or class_declaration)
                    decorators = [] # ExtractorHelpers might need TS adaptation
                    # decorators = ExtractorHelpers.extract_decorators(ast_handler, node_for_range, code_bytes) # Assuming helper works

                    class_info = {
                        'type': CodeElementType.CLASS.value,
                        'name': class_name,
                        'content': content,
                        'range': {
                            'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                            'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                        },
                        'decorators': decorators,
                        'node': class_def_node # Pass node for potential post-processing
                        # 'members' will be added by the post-processor
                    }
                    classes.append(class_info)
                    processed_node_ids.add(class_def_node.id)
                    logger.debug(f"TS Class Extractor: Extracted class '{class_name}' at line {class_info['range']['start']['line']}")
                except Exception as e:
                    logger.error(f"TS Class Extractor: Error processing class '{class_name}': {e}", exc_info=True)

        logger.debug(f'TS Class Extractor: Finished TreeSitter processing, found {len(classes)} classes.')
        return classes

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """ Extracts classes using TreeSitter. """
        if not handler: # Should be passed by ExtractionService
             logger.error("TS Class Extractor: Missing language type descriptor.")
             return []

        # --- Fetch the query string dynamically ---
        ts_query_string = self._get_ts_query_from_config()
        if not ts_query_string:
             logger.error("TS Class Extractor: Could not get TreeSitter query string.")
             return []
        # Update the handler instance ONLY if it's the specific one for this extractor instance
        # This assumes the handler passed IS the one associated via the descriptor attribute
        # A cleaner approach might involve passing the query string directly.
        if self.descriptor and self.descriptor.tree_sitter_query != ts_query_string:
             self.descriptor.tree_sitter_query = ts_query_string
        # -----------------------------------------

        elements = []
        ast_handler = self._get_ast_handler()
        if ast_handler and ts_query_string:
             try:
                 root, code_bytes = ast_handler.parse(code)
                 query_results = ast_handler.execute_query(ts_query_string, root, code_bytes)
                 elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
             except QueryError as qe:
                 logger.error(f'TS Class Extractor: TreeSitter query failed: {qe}. Query: {ts_query_string}')
             except Exception as e:
                 logger.error(f'TS Class Extractor: Error during TreeSitter extraction: {e}', exc_info=True)
        else:
             logger.warning("TS Class Extractor: Skipping TreeSitter extraction (no handler or query).")

        # Regex fallback could be added here if necessary
        # if not elements and handler and handler.regexp_pattern:
        #     # ... regex logic ...
        #     pass

        return elements

    # Regex fallback needs careful implementation if required
    # def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
    #    return []