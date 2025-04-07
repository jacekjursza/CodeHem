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
class TypeScriptMethodExtractor(TemplateExtractor):
    """ Extracts TypeScript/JavaScript methods, getters, and setters using TreeSitter. """
    LANGUAGE_CODE = 'typescript'
    # This extractor handles multiple types based on the node structure
    ELEMENT_TYPE = CodeElementType.METHOD # Primary type

    def _get_parent_class_name(self, node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[str]:
        """ Finds the name of the containing class or interface definition """
        container_node_types = ['class_declaration', 'interface_declaration', 'object_type']
        current_node = node.parent
        while current_node:
            if current_node.type in container_node_types:
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node and name_node.type in ['type_identifier', 'identifier']:
                    return ast_handler.get_node_text(name_node, code_bytes)
                # Fallback for anonymous object types or complex scenarios if needed
                return f"Container_{current_node.type}" # Placeholder name
            if current_node.type == 'program': # Stop at root
                break
            current_node = current_node.parent
        return None

    def _determine_element_type(self, definition_node: Node, ast_handler: ASTHandler) -> CodeElementType:
        """ Determines if it's a regular method, getter, or setter. """
        kind_node = definition_node.child_by_field_name('kind')
        if kind_node:
            kind_text = ast_handler.get_node_text(kind_node, b'') # Content doesn't matter for 'get'/'set'
            if kind_text == 'get':
                return CodeElementType.PROPERTY_GETTER
            elif kind_text == 'set':
                return CodeElementType.PROPERTY_SETTER
        # Check for keywords if 'kind' field is not present or inconsistent
        for child in definition_node.children:
            if child.type == 'get':
                 return CodeElementType.PROPERTY_GETTER
            if child.type == 'set':
                 return CodeElementType.PROPERTY_SETTER
        return CodeElementType.METHOD # Default

    def _extract_common_info(self, definition_node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[Dict[str, Any]]:
        """ Extracts common information (name, parameters, return type, content, range) """
        info = {}
        name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
        if not name_node:
            logger.warning(f"Could not extract name for method/property node id {definition_node.id}")
            return None

        info['name'] = ast_handler.get_node_text(name_node, code_bytes)

        # Find the node representing the full definition for range and content
        node_for_range_and_content = definition_node
        if definition_node.parent and definition_node.parent.type in ['export_statement', 'ambient_declaration']:
             node_for_range_and_content = definition_node.parent # Include export/declare keyword
        # Include decorators if present
        if node_for_range_and_content.parent and node_for_range_and_content.parent.type == 'method_definition' \
           and node_for_range_and_content.parent.child_count > 1 \
           and node_for_range_and_content.parent.child(0).type == 'decorator':
             # Need to find the top-most decorator belonging to this method
             current_search_node = node_for_range_and_content.parent
             top_decorator_node = None
             prev_sibling = current_search_node.prev_named_sibling
             while prev_sibling and prev_sibling.type == 'decorator':
                 top_decorator_node = prev_sibling
                 prev_sibling = prev_sibling.prev_named_sibling

             if top_decorator_node:
                 node_for_range_and_content = top_decorator_node # Start range from the first decorator
             else: # If no previous sibling decorator, the first one is on the parent
                 first_decorator = node_for_range_and_content.parent.child(0)
                 if first_decorator.type == 'decorator':
                      node_for_range_and_content = first_decorator

        info['content'] = ast_handler.get_node_text(node_for_range_and_content, code_bytes)
        info['range'] = {
            'start': {'line': node_for_range_and_content.start_point[0] + 1, 'column': node_for_range_and_content.start_point[1]},
            'end': {'line': definition_node.end_point[0] + 1, 'column': definition_node.end_point[1]} # End range at the method definition itself
        }
        # Adjust end range if body exists and is after definition node
        body_node = ast_handler.find_child_by_field_name(definition_node, 'body')
        if body_node:
            info['range']['end'] = {'line': body_node.end_point[0] + 1, 'column': body_node.end_point[1]}

        info['definition_start_line'] = definition_node.start_point[0] + 1
        info['definition_start_col'] = definition_node.start_point[1]

        params_node = ast_handler.find_child_by_field_name(definition_node, 'parameters')
        info['parameters'] = ExtractorHelpers.extract_parameters(ast_handler, params_node, code_bytes, is_self_or_this=False) # TS doesn't use self/cls explicitly

        return_type_node = ast_handler.find_child_by_field_name(definition_node, 'return_type')
        return_type = None
        if return_type_node:
             return_type = ast_handler.get_node_text(return_type_node, code_bytes)
             # Clean up ': ' prefix if present from simple text extraction
             if return_type and isinstance(return_type, str) and return_type.startswith(':'):
                 return_type = return_type[1:].strip()

        # Extract return values from body (basic implementation)
        return_values = []
        if body_node:
            try:
                # Simple query for return statements with values
                return_query = "(return_statement (_) @return_value)"
                return_results = ast_handler.execute_query(return_query, body_node, code_bytes)
                for r_node, r_capture in return_results:
                    if r_capture == 'return_value':
                        parent_stmt = r_node.parent
                        if parent_stmt and parent_stmt.type == 'return_statement':
                           val_text = ast_handler.get_node_text(r_node, code_bytes)
                           if val_text not in return_values:
                               return_values.append(val_text)
            except Exception as e:
                logger.warning(f"Could not query return values for {info.get('name', 'unknown method')}: {e}", exc_info=False)

        info['return_info'] = {'return_type': return_type, 'return_values': return_values}

        return info

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Processes TreeSitter query results for methods, getters, setters. """
        elements = []
        processed_definition_node_ids = set()
        logger.debug(f'TS Method Extractor: Processing {len(query_results)} captures.')

        # Use a map to collect info based on definition node ID
        node_map: Dict[int, Dict[str, Any]] = {}

        for node, capture_name in query_results:
            definition_node = None
            # Identify the core definition node based on captures
            if capture_name == 'method_def':
                 if node.type == 'method_definition':
                      definition_node = node
                 else:
                     logger.warning(f"Capture 'method_def' on unexpected node type: {node.type}")
                     continue
            elif capture_name in ['method_name', 'params', 'return_type', 'body']:
                 # Find the parent method_definition node
                 parent_def = ast_handler.find_parent_of_type(node, 'method_definition')
                 if parent_def:
                     definition_node = parent_def
                 else:
                     continue # Skip captures not within a method_definition

            if definition_node:
                node_id = definition_node.id
                if node_id not in processed_definition_node_ids:
                    if node_id not in node_map:
                         # Ensure it's inside a class/interface before proceeding
                         class_name = self._get_parent_class_name(definition_node, ast_handler, code_bytes)
                         if class_name:
                              node_map[node_id] = {'definition_node': definition_node, 'class_name': class_name}
                         else:
                              # It's likely a function, not a method, mark as processed and skip
                              processed_definition_node_ids.add(node_id)
                              continue # Skip if not inside a class/interface context

                    # Store related nodes if the definition is valid (in a class)
                    if node_id in node_map:
                        if capture_name == 'method_name':
                            node_map[node_id]['name_node'] = node
                        elif capture_name == 'params':
                            node_map[node_id]['params_node'] = node
                        elif capture_name == 'return_type':
                            node_map[node_id]['return_type_node'] = node
                        elif capture_name == 'body':
                             node_map[node_id]['body_node'] = node

        # Now process the collected information for each unique definition node
        for node_id, data in node_map.items():
            if node_id in processed_definition_node_ids:
                continue

            definition_node = data['definition_node']
            class_name = data['class_name']

            common_info = self._extract_common_info(definition_node, ast_handler, code_bytes)
            if common_info:
                element_name = common_info['name']
                element_type = self._determine_element_type(definition_node, ast_handler)
                # Use ExtractorHelpers for decorators associated with the definition or its parent export/decorated node
                decorators = ExtractorHelpers.extract_decorators(ast_handler, definition_node, code_bytes)

                element_info = {
                    'type': element_type.value,
                    'name': element_name,
                    'content': common_info['content'],
                    'class_name': class_name,
                    'range': common_info['range'],
                    'decorators': decorators,
                    'parameters': common_info['parameters'],
                    'return_info': common_info['return_info'],
                    'definition_start_line': common_info['definition_start_line'],
                    'definition_start_col': common_info['definition_start_col'],
                    'node': definition_node # Include node for potential post-processing use
                }
                elements.append(element_info)
                processed_definition_node_ids.add(node_id)
                logger.debug(f"TS Method Extractor: Processed '{class_name}.{element_name}' as type '{element_type.value}'")
            else:
                logger.warning(f"TS Method Extractor: Failed to extract common info for node id {node_id} in class '{class_name}'.")
                processed_definition_node_ids.add(node_id)

        logger.debug(f'TS Method Extractor: Finished processing. Found {len(elements)} methods/getters/setters.')
        return elements

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """ Regex fallback is less reliable for TS methods/getters/setters. """
        logger.warning("Regex fallback not implemented for TypeScriptMethodExtractor.")
        return []