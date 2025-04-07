# -*- coding: utf-8 -*-
import logging
from typing import Dict, List, Any, Tuple, Optional
from tree_sitter import Node, QueryError
from codehem.core.extractors.type_function import FunctionExtractor # Assuming this base exists
from codehem.models.enums import CodeElementType
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.core.registry import extractor, registry # Keep registry import if needed elsewhere
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class TypeScriptFunctionExtractor(FunctionExtractor):
    """ Extracts TypeScript/JavaScript functions (declarations and arrows) using configured TreeSitter queries. """
    LANGUAGE_CODE = 'typescript'
    ELEMENT_TYPE = CodeElementType.FUNCTION

    # No longer needed: def _get_ts_query_from_config(self) -> Optional[str]:

    def _extract_parameters_ts(self, params_node: Optional[Node], ast_handler: ASTHandler, code_bytes: bytes) -> List[Dict]:
        """ Extracts parameters specifically for TS grammar (from previous implementation). """
        parameters = []
        if not params_node or params_node.type != 'formal_parameters':
             # Handle case for simple arrow functions like `x => x * 2` where params_node might be just identifier
            if params_node and params_node.type == 'identifier':
                 name = ast_handler.get_node_text(params_node, code_bytes)
                 parameters.append({'name': name, 'type': None, 'default': None, 'optional': False})
                 return parameters
            # logger.debug(f"_extract_parameters_ts: No formal_parameters node found or node type is {params_node.type if params_node else 'None'}")
            return parameters

        for param_child in params_node.children:
            param_info = {'name': None, 'type': None, 'default': None, 'optional': False}
            node_type = param_child.type
            try:
                # Logic from previous implementation - seems reasonable
                if node_type == 'required_parameter':
                    pattern_node = param_child.child_by_field_name('pattern') or (param_child.child(0) if param_child.child_count > 0 else None)
                    type_node = param_child.child_by_field_name('type')
                    if pattern_node:
                         param_info['name'] = ast_handler.get_node_text(pattern_node, code_bytes)
                    if type_node:
                         param_info['type'] = ast_handler.get_node_text(type_node.child(0), code_bytes) # type is inside type_annotation
                elif node_type == 'optional_parameter':
                    param_info['optional'] = True
                    pattern_node = param_child.child_by_field_name('pattern') or (param_child.child(0) if param_child.child_count > 0 else None)
                    type_node = param_child.child_by_field_name('type')
                    value_node = param_child.child_by_field_name('value') # For default value
                    if pattern_node:
                         param_info['name'] = ast_handler.get_node_text(pattern_node, code_bytes)
                    if type_node:
                         param_info['type'] = ast_handler.get_node_text(type_node.child(0), code_bytes)
                    if value_node: # Handle default value for optional parameter
                        param_info['default'] = ast_handler.get_node_text(value_node, code_bytes)
                elif node_type == 'rest_parameter':
                     # TS grammar might use '...' token then identifier
                     name_node = param_child.child(1) if param_child.child_count > 1 and param_child.child(1).type == 'identifier' else None
                     type_node = param_child.child_by_field_name('type')
                     if name_node:
                         param_info['name'] = '...' + ast_handler.get_node_text(name_node, code_bytes)
                     if type_node:
                         param_info['type'] = ast_handler.get_node_text(type_node.child(0), code_bytes)
                     param_info['optional'] = True # Rest parameters are implicitly optional array-like

                # Add other TS parameter types if necessary (e.g., pattern bindings)

                if param_info['name']:
                    parameters.append(param_info)
                elif node_type not in [',', '(', ')']:
                    logger.warning(f'Could not extract name for parameter node type {node_type}: {ast_handler.get_node_text(param_child, code_bytes)}')
            except Exception as e:
                logger.error(f'Error processing parameter node type {node_type}: {e}', exc_info=True)
        return parameters

    def _extract_return_type_ts(self, func_def_node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[str]:
        """ Extracts return type specifically for TS grammar. """
        # Check both function_declaration and arrow_function nodes
        return_type_node = func_def_node.child_by_field_name('return_type')
        if return_type_node and return_type_node.type == 'type_annotation':
            if return_type_node.child_count > 0:
                type_node = return_type_node.child(0)
                return ast_handler.get_node_text(type_node, code_bytes)
        return None

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process tree-sitter query results for functions, including arrow functions. """
        functions = []
        processed_node_ids = set()
        node_map = {} # Store parts related to a function node ID

        for node, capture_name in query_results:
             # Identify the main definition node (function_declaration or arrow_function)
            current_def_node = None
            node_for_range = None # Node to use for start/end range (might include export)
            is_arrow = False

            if capture_name in ['function_def', 'function_def_exported']:
                node_for_range = node
                current_def_node = node if node.type == 'function_declaration' else node.child_by_field_name('declaration')
            elif capture_name in ['arrow_function_def', 'arrow_function_def_exported']:
                 node_for_range = node
                 # Navigate to the arrow_function node within lexical_declaration/variable_declarator
                 lex_decl = node if node.type == 'lexical_declaration' else node.child_by_field_name('declaration')
                 if lex_decl and lex_decl.child_count > 0 and lex_decl.child(0).type == 'variable_declarator':
                     var_decl = lex_decl.child(0)
                     arrow_func_node = var_decl.child_by_field_name('value')
                     if arrow_func_node and arrow_func_node.type == 'arrow_function':
                         current_def_node = arrow_func_node
                         is_arrow = True
            elif capture_name == 'function_name':
                # Find containing function_declaration or variable_declarator->arrow_function
                parent_func_decl = ast_handler.find_parent_of_type(node, 'function_declaration')
                parent_var_decl = ast_handler.find_parent_of_type(node, 'variable_declarator')
                if parent_func_decl:
                    current_def_node = parent_func_decl
                    export_parent = ast_handler.find_parent_of_type(current_def_node, 'export_statement')
                    node_for_range = export_parent or current_def_node
                elif parent_var_decl:
                    arrow_func = parent_var_decl.child_by_field_name('value')
                    if arrow_func and arrow_func.type == 'arrow_function':
                        current_def_node = arrow_func
                        is_arrow = True
                        # Find range from lexical_declaration or export_statement
                        lex_decl = ast_handler.find_parent_of_type(parent_var_decl, 'lexical_declaration')
                        export_parent = ast_handler.find_parent_of_type(lex_decl or parent_var_decl, 'export_statement')
                        node_for_range = export_parent or lex_decl or parent_var_decl
            elif capture_name in ['params', 'return_type', 'body', 'arrow_func_body']:
                 parent_def = ast_handler.find_parent_of_type(node, ['function_declaration', 'arrow_function'])
                 if parent_def:
                     current_def_node = parent_def
                     # Need to determine the node_for_range based on parent structure (export, lexical)
                     if parent_def.type == 'function_declaration':
                          export_parent = ast_handler.find_parent_of_type(parent_def, 'export_statement')
                          node_for_range = export_parent or parent_def
                     elif parent_def.type == 'arrow_function':
                          var_decl = ast_handler.find_parent_of_type(parent_def, 'variable_declarator')
                          lex_decl = ast_handler.find_parent_of_type(var_decl, 'lexical_declaration')
                          export_parent = ast_handler.find_parent_of_type(lex_decl or var_decl, 'export_statement')
                          node_for_range = export_parent or lex_decl or var_decl
                          is_arrow = True

            if current_def_node and node_for_range:
                 node_id = current_def_node.id
                 if node_id not in node_map:
                     node_map[node_id] = {'node': current_def_node, 'range_node': node_for_range, 'is_arrow': is_arrow}
                 # Update range node if a higher level one (like export) is found later
                 if node_for_range.start_byte < node_map[node_id]['range_node'].start_byte:
                      node_map[node_id]['range_node'] = node_for_range

                 # Store specific parts
                 if capture_name == 'function_name':
                     node_map[node_id]['name_node'] = node
                 elif capture_name == 'params':
                     node_map[node_id]['params_node'] = node
                 elif capture_name == 'return_type':
                     node_map[node_id]['return_type_node'] = node

        # Process the assembled node information
        for node_id, parts in node_map.items():
            if node_id in processed_node_ids:
                continue

            func_def_node = parts.get('node')
            node_for_range = parts.get('range_node')
            is_arrow = parts.get('is_arrow', False)

            # Exclude methods defined inside classes
            parent_class = ast_handler.find_parent_of_type(func_def_node, ['class_declaration', 'abstract_class_declaration'])
            if parent_class:
                 processed_node_ids.add(node_id)
                 continue

            # Get name (different for arrow functions)
            func_name = None
            if is_arrow:
                 # Name comes from the variable_declarator
                 var_decl = ast_handler.find_parent_of_type(func_def_node, 'variable_declarator')
                 name_node = ast_handler.find_child_by_field_name(var_decl, 'name') if var_decl else None
                 if name_node: func_name = ast_handler.get_node_text(name_node, code_bytes)
            else:
                 # Name from function_declaration itself
                 name_node = ast_handler.find_child_by_field_name(func_def_node, 'name')
                 if name_node: func_name = ast_handler.get_node_text(name_node, code_bytes)

            if not func_name:
                 logger.warning(f"Could not extract name for function node id {node_id}")
                 processed_node_ids.add(node_id)
                 continue

            try:
                content = ast_handler.get_node_text(node_for_range, code_bytes)
                start_point = node_for_range.start_point
                end_point = node_for_range.end_point

                params_node = parts.get('params_node') or func_def_node.child_by_field_name('parameters')
                # Special case for simple arrow: x => ... param node is identifier directly
                if not params_node and is_arrow and func_def_node.child_count > 0 and func_def_node.child(0).type == 'identifier':
                     params_node = func_def_node.child(0)

                parameters = self._extract_parameters_ts(params_node, ast_handler, code_bytes)
                return_type = self._extract_return_type_ts(func_def_node, ast_handler, code_bytes)
                return_info = {'return_type': return_type, 'return_values': []} # Return value extraction needs specific logic

                # Decorators are less common on standalone functions in TS/JS but check if needed
                decorators = []

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
                    'node': func_def_node, # Store the core function/arrow node
                    'is_arrow': is_arrow,
                    'definition_start_line': func_def_node.start_point[0] + 1
                }
                functions.append(function_info)
                processed_node_ids.add(node_id)
                logger.debug(f"TS Function Extractor: Extracted function '{func_name}' (Arrow: {is_arrow}) at line {function_info['range']['start']['line']}")

            except Exception as e:
                logger.error(f"TS Function Extractor: Error processing function '{func_name}' (node id {node_id}): {e}", exc_info=True)

        logger.debug(f'TS Function Extractor: Finished TreeSitter processing, found {len(functions)} functions.')
        return functions

    def _extract_with_patterns(self, code: str, handler: Optional[ElementTypeLanguageDescriptor], context: Dict[str, Any]) -> List[Dict]:
        """ Extracts functions using TreeSitter based on the provided handler's query. """
        if not handler or not handler.tree_sitter_query:
            logger.error(f'TS Function Extractor: Missing language type descriptor or TreeSitter query for {self.ELEMENT_TYPE.value}.')
            return []

        elements = []
        ast_handler = self._get_ast_handler()
        if ast_handler:
            try:
                logger.debug(f"TS Function Extractor: Using TreeSitter query from handler: {handler.tree_sitter_query}")
                root, code_bytes = ast_handler.parse(code)
                query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
                elements = self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)
            except QueryError as qe:
                logger.error(f'TS Function Extractor: TreeSitter query failed: {qe}. Query: {handler.tree_sitter_query}')
            except Exception as e:
                logger.error(f'TS Function Extractor: Error during TreeSitter extraction: {e}', exc_info=True)
        else:
            logger.warning('TS Function Extractor: AST handler not available, skipping TreeSitter extraction.')

        # Remove or simplify Regex fallback if TreeSitter is reliable
        # if not elements and handler.regexp_pattern:
        #    logger.warning('TS Function Extractor: Regex fallback is currently disabled/not implemented.')
            # elements = self._process_regex_results(...)

        return elements

    def _process_regex_results(self, matches, code, context) -> List[Dict]:
        # Implement or remove this if Regex fallback is needed/not needed
        logger.warning("TS Function Extractor: Regex processing not implemented.")
        return []