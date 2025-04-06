import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.type_function import FunctionExtractor # Use base FunctionExtractor
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry
from codehem.core.engine.ast_handler import ASTHandler
# Import helper or wrapper if adapted for TS
from codehem.core.extractors.extraction_base import ExtractorHelpers
# from codehem.core.engine.code_node_wrapper import CodeNodeWrapper # If using this

logger = logging.getLogger(__name__)

@extractor
class TypeScriptFunctionExtractor(FunctionExtractor):
    """ Extracts TypeScript/JavaScript function declarations and arrow functions. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.FUNCTION

    def __init__(self, language_code: str, language_type_descriptor: Optional[ElementTypeLanguageDescriptor]):
        super().__init__(language_code, language_type_descriptor)
        # Patterns will be fetched dynamically if needed

    def _get_ts_query_from_config(self) -> Optional[str]:
        """ Helper to fetch the TS function query string directly from config. """
        try:
            lang_config = registry.get_language_config(self.language_code)
            if lang_config:
                placeholders = lang_config.get('template_placeholders', {}).get(self.ELEMENT_TYPE, {})
                if placeholders:
                    # Get the query defined in config.py
                    ts_query = placeholders.get('tree_sitter_query')
                    if not ts_query:
                         # Fallback query if not defined in config
                         ts_query = """
                         (function_declaration
                           name: (identifier) @function_name
                         ) @function_def

                         (export_statement
                           declaration: (function_declaration
                             name: (identifier) @function_name
                           ) @function_def_exported
                         )

                         (lexical_declaration
                           (variable_declarator
                             name: (identifier) @function_name
                             value: (arrow_function) @arrow_func_body
                           )
                         ) @arrow_function_def

                         (export_statement
                           declaration: (lexical_declaration
                            (variable_declarator
                                name: (identifier) @function_name
                                value: (arrow_function) @arrow_func_body
                            )) @arrow_function_def_exported
                         )
                         """
                         logger.warning("Using fallback TS function query string.")
                    logger.debug(f"Fetched TS function query from config/fallback: {ts_query}")
                    return ts_query.strip()
                else:
                    logger.warning(f"No placeholders found for {self.ELEMENT_TYPE} in TS config.")
            else:
                logger.error("Could not retrieve TS language configuration from registry.")
        except Exception as e:
            logger.error(f"Error fetching TS function query from config: {e}", exc_info=True)
        return None

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process tree-sitter query results for functions and arrow functions. """
        functions = []
        processed_node_ids = set()
        logger.debug(f"TS Function Extractor: Processing {len(query_results)} captures.")

        for node, capture_name in query_results:
            func_def_node = None
            func_name_node = None
            func_body_node = None
            node_for_range = node # Default node for range/content
            is_arrow = False

            if capture_name in ["function_def", "function_def_exported"]:
                func_def_node = node if capture_name == "function_def" else node.child_by_field_name('declaration')
                if not func_def_node or func_def_node.type != 'function_declaration': continue
                func_name_node = func_def_node.child_by_field_name('name')
                func_body_node = func_def_node.child_by_field_name('body')
                if capture_name == "function_def_exported": node_for_range = node # Use export_statement for full range

            elif capture_name in ["arrow_function_def", "arrow_function_def_exported"]:
                 var_declarator = node.child(0) if capture_name == "arrow_function_def" else node.child_by_field_name('declaration').child(0)
                 if not var_declarator or var_declarator.type != 'variable_declarator': continue
                 func_name_node = var_declarator.child_by_field_name('name')
                 arrow_func_node = var_declarator.child_by_field_name('value')
                 if not arrow_func_node or arrow_func_node.type != 'arrow_function': continue
                 func_def_node = arrow_func_node # Treat arrow func node as the 'definition'
                 func_body_node = arrow_func_node.child_by_field_name('body')
                 is_arrow = True
                 if capture_name == "arrow_function_def_exported": node_for_range = node # Use export_statement for full range
                 else: node_for_range = node # Use lexical_declaration for range

            elif capture_name == "function_name": # If only name is captured
                func_name_node = node
                # Try to find associated definition node (could be function_declaration or arrow_function's parent declarator)
                parent_func_decl = ast_handler.find_parent_of_type(node, 'function_declaration')
                parent_var_decl = ast_handler.find_parent_of_type(node, 'variable_declarator')

                if parent_func_decl:
                    func_def_node = parent_func_decl
                    node_for_range = func_def_node # Check for export statement later
                elif parent_var_decl and parent_var_decl.child_by_field_name('value').type == 'arrow_function':
                    func_def_node = parent_var_decl.child_by_field_name('value')
                    parent_lex_decl = ast_handler.find_parent_of_type(parent_var_decl, 'lexical_declaration')
                    node_for_range = parent_lex_decl if parent_lex_decl else parent_var_decl
                    is_arrow = True
                else:
                    continue # Only name found, cannot process further

                # Adjust node_for_range if it's part of an export
                export_stmt = ast_handler.find_parent_of_type(node_for_range, "export_statement")
                if export_stmt: node_for_range = export_stmt

            # Process if we found a valid definition node not yet processed
            if func_def_node and func_def_node.id not in processed_node_ids:
                 # Ensure it's not actually a method inside a class
                 parent_class = ast_handler.find_parent_of_type(func_def_node, 'class_declaration')
                 if parent_class:
                      processed_node_ids.add(func_def_node.id) # Mark as processed to avoid re-checking
                      logger.debug(f"  Skipping node {func_def_node.id} as it's inside class {ast_handler.get_node_text(parent_class.child_by_field_name('name'), code_bytes)}")
                      continue

                 if func_name_node:
                     func_name = ast_handler.get_node_text(func_name_node, code_bytes)
                 else:
                     logger.warning(f"Could not extract name for function node id {func_def_node.id}")
                     continue

                 try:
                    content = ast_handler.get_node_text(node_for_range, code_bytes)
                    start_point = node_for_range.start_point
                    end_point = node_for_range.end_point

                    # --- TODO: Adapt Helpers for TypeScript ---
                    # Parameters might be in func_def_node or arrow_func_node for arrow functions
                    param_source_node = func_def_node
                    parameters = ExtractorHelpers.extract_parameters(ast_handler, param_source_node, code_bytes, is_self_or_this=False) # is_self=False for functions
                    # Return info might need adaptation for arrow function implicit returns
                    return_info = ExtractorHelpers.extract_return_info(ast_handler, param_source_node, code_bytes)
                    # Decorators are less common on standalone functions in TS but possible
                    decorators = [] # ExtractorHelpers.extract_decorators(...) if applicable
                    # ------------------------------------------

                    function_info = {
                        'type': CodeElementType.FUNCTION.value,
                        'name': func_name,
                        'content': content,
                        'range': {
                            'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                            'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                        },
                        'parameters': parameters,
                        'return_info': return_info,
                        'decorators': decorators,
                        'node': func_def_node, # Node for definition details
                        'is_arrow': is_arrow,
                        # Use definition node's start line for sorting/reference
                        'definition_start_line': func_def_node.start_point[0] + 1
                    }
                    functions.append(function_info)
                    processed_node_ids.add(func_def_node.id)
                    # Add declarator ID too if it was arrow to prevent duplicate processing via name capture
                    if is_arrow and parent_var_decl: processed_node_ids.add(parent_var_decl.id)

                    logger.debug(f"TS Function Extractor: Extracted function '{func_name}' (Arrow: {is_arrow}) at line {function_info['range']['start']['line']}")
                 except Exception as e:
                    logger.error(f"TS Function Extractor: Error processing function '{func_name}': {e}", exc_info=True)

        logger.debug(f'TS Function Extractor: Finished TreeSitter processing, found {len(functions)} functions.')
        return functions

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """ Extracts functions using TreeSitter. """
        if not handler:
            logger.error("TS Function Extractor: Missing language type descriptor.")
            return []

        ts_query_string = self._get_ts_query_from_config()
        if not ts_query_string:
            logger.error("TS Function Extractor: Could not get TreeSitter query string.")
            return []

        elements = []
        ast_handler = self._get_ast_handler()
        if ast_handler:
             try:
                 root, code_bytes = ast_handler.parse(code)
                 query_results = ast_handler.execute_query(ts_query_string, root, code_bytes)
                 elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
             except QueryError as qe:
                 logger.error(f'TS Function Extractor: TreeSitter query failed: {qe}. Query: {ts_query_string}')
             except Exception as e:
                 logger.error(f'TS Function Extractor: Error during TreeSitter extraction: {e}', exc_info=True)
        else:
             logger.warning("TS Function Extractor: Skipping TreeSitter extraction (no handler).")

        # Regex fallback could be added here if necessary
        # if not elements and handler.regexp_pattern:
        #     pass

        return elements

    # Regex fallback needs careful implementation if required
    # def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
    #     return []