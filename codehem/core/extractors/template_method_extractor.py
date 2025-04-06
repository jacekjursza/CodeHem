import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from tree_sitter import Node

from codehem.core.extractors.extraction_base import ExtractorHelpers, TemplateExtractor
from codehem.core.registry import extractor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
from codehem.models.enums import CodeElementType

logger = logging.getLogger(__name__)

@extractor
class TemplateMethodExtractor(TemplateExtractor):
    """
    Consolidated extractor for methods, getters, and setters.
    Version 8.
    --- CHANGES ---
    - Improved _extract_all_decorators for better name recognition (identifier, attribute, call).
    - Improved _determine_element_type for correct recognition of PROPERTY_GETTER and PROPERTY_SETTER.
    """
    ELEMENT_TYPE = CodeElementType.METHOD  # Base type, will be refined

    def __init__(self, language_code: str, language_type_descriptor: ElementTypeLanguageDescriptor):
        super().__init__(language_code, language_type_descriptor)
        if not self.descriptor or not (self.descriptor.tree_sitter_query or self.descriptor.regexp_pattern):
             logger.warning(f'Descriptor for {language_code}/{self.ELEMENT_TYPE.value} did not provide patterns.')

    def _get_actual_parent_class_name(self, node: Node, ast_handler: Any, code_bytes: bytes) -> Optional[str]:
        """ Finds the name of the containing class definition """
        class_node_types = ['class_definition', 'class_declaration'] # Add other language-specific class types if needed
        current_node = node.parent
        while current_node:
            if current_node.type in class_node_types:
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node:
                    return ast_handler.get_node_text(name_node, code_bytes)
                else:
                    # Fallback for languages where name isn't a field (e.g., TypeScript type_identifier)
                    for child in current_node.children:
                        if child.type in ['identifier', 'type_identifier']: # Add other relevant node types
                             return ast_handler.get_node_text(child, code_bytes)
                return None # Class node found, but couldn't determine name
            current_node = current_node.parent
        return None # No containing class node found

    def _extract_all_decorators(self, definition_node: Node, ast_handler: Any, code_bytes: bytes) -> List[Dict[str, Any]]:
        """Extracts all decorators associated with the given definition node (Improved version)."""
        decorators = []
        parent_node = definition_node.parent
        if parent_node and parent_node.type == 'decorated_definition':
            for child_idx, child in enumerate(parent_node.children):
                if child.type == 'decorator':
                    decorator_content = ast_handler.get_node_text(child, code_bytes)
                    decorator_name = None

                    # Try to find the actual name node within the decorator structure
                    # Python specific: often starts with '@', then expression
                    actual_name_node = child.child(0)
                    if actual_name_node and actual_name_node.type == 'expression_statement' and actual_name_node.child_count > 0:
                         actual_name_node = actual_name_node.child(0) # Dive into expression
                    elif actual_name_node and actual_name_node.type == '@':
                         # Skip the '@' symbol itself if present
                         if child.child_count > 1:
                              actual_name_node = child.child(1)
                         else:
                              actual_name_node = None # Decorator is just "@" ? Unlikely but handle

                    if actual_name_node:
                        node_type = actual_name_node.type
                        logger.debug(f"    _extract_all_decorators: Analyzing name node of type '{node_type}' for: {decorator_content}")

                        if node_type == 'identifier':
                            decorator_name = ast_handler.get_node_text(actual_name_node, code_bytes)
                            logger.debug(f"      -> Recognized 'identifier': name='{decorator_name}'")
                        elif node_type == 'attribute': # e.g., property_name.setter
                            obj_node = ast_handler.find_child_by_field_name(actual_name_node, 'object')
                            attr_node = ast_handler.find_child_by_field_name(actual_name_node, 'attribute')
                            if obj_node and attr_node and obj_node.type == 'identifier' and attr_node.type == 'identifier':
                                obj_name = ast_handler.get_node_text(obj_node, code_bytes)
                                attr_name = ast_handler.get_node_text(attr_node, code_bytes)
                                decorator_name = f'{obj_name}.{attr_name}'
                                logger.debug(f"      -> Recognized 'attribute': object='{obj_name}', attribute='{attr_name}' -> name='{decorator_name}'")
                            else:
                                logger.warning(f"      -> Incomplete or unexpected 'attribute' node: obj={(obj_node.type if obj_node else 'None')}, attr={(attr_node.type if attr_node else 'None')} in {decorator_content}")
                        elif node_type == 'call': # e.g., @my_decorator(arg=1)
                             func_node = ast_handler.find_child_by_field_name(actual_name_node, 'function')
                             if func_node:
                                 if func_node.type == 'identifier':
                                     decorator_name = ast_handler.get_node_text(func_node, code_bytes)
                                     logger.debug(f"      -> Recognized 'call(identifier)': name='{decorator_name}'")
                                 elif func_node.type == 'attribute':
                                     obj_node = ast_handler.find_child_by_field_name(func_node, 'object')
                                     attr_node = ast_handler.find_child_by_field_name(func_node, 'attribute')
                                     if obj_node and attr_node and obj_node.type == 'identifier' and attr_node.type == 'identifier':
                                         obj_name = ast_handler.get_node_text(obj_node, code_bytes)
                                         attr_name = ast_handler.get_node_text(attr_node, code_bytes)
                                         decorator_name = f'{obj_name}.{attr_name}'
                                         logger.debug(f"      -> Recognized 'call(attribute)': object='{obj_name}', attribute='{attr_name}' -> name='{decorator_name}'")
                                     else:
                                         logger.warning(f"      -> Incomplete 'attribute' in decorator call: obj={(obj_node.type if obj_node else 'None')}, attr={(attr_node.type if attr_node else 'None')} in {decorator_content}")
                                 else:
                                     logger.warning(f"      -> Unexpected function type '{func_node.type}' in decorator call: {decorator_content}")
                             else:
                                 logger.warning(f'      -> Missing function node in decorator call: {decorator_content}')
                        else:
                             logger.warning(f"    _extract_all_decorators: Unsupported main decorator name node type '{node_type}': {decorator_content}")
                    else:
                         logger.warning(f'    _extract_all_decorators: Could not find name node inside decorator: {decorator_content}')

                    # Fallback name extraction if specific parsing failed
                    if decorator_name is None:
                        decorator_name = decorator_content.lstrip('@').strip() # Basic fallback
                        logger.warning(f'    _extract_all_decorators: Used fallback for decorator name: "{decorator_name}" from {decorator_content}')

                    # Calculate range for the decorator node itself
                    dec_range_dict = {
                        'start_line': child.start_point[0] + 1, 'start_column': child.start_point[1],
                        'end_line': child.end_point[0] + 1, 'end_column': child.end_point[1]
                    }
                    decorators.append({'name': decorator_name, 'content': decorator_content, 'range': dec_range_dict})
                    logger.debug(f"    _extract_all_decorators: Finally added decorator [{child_idx}]: name='{decorator_name}', content='{decorator_content[:50]}...'")

        return decorators

    def _extract_common_info(self, definition_node: Node, ast_handler: Any, code_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Extracts common information (name, parameters, return type, content, range)."""
        from codehem.core.engine.code_node_wrapper import CodeNodeWrapper
        wrapper = CodeNodeWrapper(ast_handler, definition_node, code_bytes, language_code=ast_handler.language_code)
        info = {}
        info['name'] = wrapper.get_name()
        info['parameters'] = wrapper.get_parameters(skip_self_or_cls=True)
        info['return_info'] = wrapper.get_return_info()

        # Determine the node to use for overall range and content (includes decorators)
        parent_node = definition_node.parent
        node_for_range_and_content = definition_node
        if parent_node and parent_node.type == 'decorated_definition':
             node_for_range_and_content = parent_node
             logger.debug(f"    _extract_common_info: Element '{info['name']}' is decorated, used parent node for range/content.")

        try:
            info['content'] = ast_handler.get_node_text(node_for_range_and_content, code_bytes)
            info['range'] = {
                'start': {'line': node_for_range_and_content.start_point[0] + 1, 'column': node_for_range_and_content.start_point[1]},
                'end': {'line': node_for_range_and_content.end_point[0] + 1, 'column': node_for_range_and_content.end_point[1]}
            }
            # Also store the start line of the actual definition (excluding decorators)
            info['definition_start_line'] = definition_node.start_point[0] + 1
            info['definition_start_col'] = definition_node.start_point[1]
        except Exception as e:
             logger.error(f"Error getting content/range for node id {node_for_range_and_content.id} (name: {info.get('name', 'N/A')}): {e}", exc_info=True)
             return None # If we can't get basic info, skip this element

        return info

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: Any, context: Dict[str, Any]) -> List[Dict]:
        """
        Processes TreeSitter query results for potential methods.
        Assigns provisional 'method' type; specific classification (getter/setter)
        is deferred to the language-specific post-processor.
        """
        potential_elements = []
        processed_definition_node_ids = set()
        logger.debug(f'_process_tree_sitter_results: Received {len(query_results)} results from TreeSitter query.')

        for node, capture_name in query_results:
            definition_node = None
            # Identify the core function definition node from captures like 'method_def', 'decorated_method_def', or name captures
            if capture_name in ['method_def', 'decorated_method_def']:
                 potential_def = node
                 if node.type == 'decorated_definition':
                      def_child = ast_handler.find_child_by_field_name(node, 'definition')
                      if def_child and def_child.type == 'function_definition':
                           definition_node = def_child
                      else: # Fallback if structure is unexpected
                           definition_node = node # Keep the decorated_definition node for range? Revisit needed.
                           logger.warning(f"Could not find 'function_definition' child within 'decorated_definition' node ID {node.id}")
                           # Attempt to find name anyway for logging/debugging
                           temp_name_node = ast_handler.find_child_by_field_name(node, 'name') or \
                                            (def_child and ast_handler.find_child_by_field_name(def_child, 'name'))
                           temp_name = ast_handler.get_node_text(temp_name_node, code_bytes) if temp_name_node else "UNKNOWN"
                           logger.warning(f"  Decorated definition name (approx): {temp_name}")

                 elif node.type == 'function_definition':
                      definition_node = node
                 else:
                     logger.warning(f"Unexpected node type '{node.type}' captured as '{capture_name}'")

            elif capture_name in ['method_name', 'property_name', 'function_name']: # Handle cases where name is captured directly
                parent_func = ast_handler.find_parent_of_type(node, 'function_definition')
                if parent_func:
                    definition_node = parent_func
                else:
                     # Could be a name capture outside a function def context, ignore
                     logger.debug(f"Name capture '{capture_name}' found outside function_definition context.")
                     continue # Skip this capture if it's not part of a function definition

            # Process if we found a valid definition node not already processed
            if definition_node and definition_node.id not in processed_definition_node_ids:
                # Check if it's within a class context
                class_name = self._get_actual_parent_class_name(definition_node, ast_handler, code_bytes)
                if class_name: # Only process if it's actually a method (inside a class)
                    logger.debug(f"  _process_tree_sitter_results: Processing definition (Node ID: {definition_node.id}) in class '{class_name}'.")
                    common_info = self._extract_common_info(definition_node, ast_handler, code_bytes)
                    if common_info:
                        element_name = common_info['name']
                        # Extract decorators but DO NOT classify type here
                        decorators = self._extract_all_decorators(definition_node, ast_handler, code_bytes)

                        # Assign provisional type METHOD - Post processor will refine
                        provisional_type = CodeElementType.METHOD.value

                        element_info = {
                            'node_id': definition_node.id, # Temporary ID for deduplication
                            'type': provisional_type, # Provisional type
                            'name': element_name,
                            'content': common_info['content'],
                            'class_name': class_name,
                            'range': common_info['range'],
                            'decorators': decorators, # Pass raw decorator info
                            'parameters': common_info['parameters'],
                            'return_info': common_info['return_info'],
                            'definition_start_line': common_info['definition_start_line'],
                            'definition_start_col': common_info['definition_start_col']
                        }
                        potential_elements.append(element_info)
                        processed_definition_node_ids.add(definition_node.id)
                    else:
                        logger.warning(f'  _process_tree_sitter_results: Failed to extract common_info for node id {definition_node.id}.')
                else:
                     logger.debug(f"  _process_tree_sitter_results: Skipping definition node id {definition_node.id} - not inside a class.")

        # Final processing: remove temporary node_id and return
        final_results = []
        for elem in potential_elements:
            logger.debug(f"Processed extractor result: {elem.get('class_name')}.{elem.get('name')} as provisional type {elem.get('type')}")
            elem.pop('node_id', None) # Remove temporary ID
            final_results.append(elem)

        logger.debug(f'Finished TreeSitter processing in TemplateMethodExtractor. Returned {len(final_results)} potential methods.')
        return final_results

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """Processes regex match results (currently lower priority)."""
        # This regex implementation is likely basic and may need significant enhancement
        # or removal if TreeSitter proves sufficient.
        logger.warning('Regex processing in TemplateMethodExtractor requires verification/enhancement.')
        results = []
        class_name = context.get('class_name') if context else None # Regex needs class context passed in

        for match in matches:
            try:
                name = match.group(1) # Assuming first group is the name
                content = match.group(0) # Full match content
                start_pos, end_pos = match.span()
                start_line = code[:start_pos].count('\n') + 1
                # Regex end_line calculation might be inaccurate for multi-line methods
                end_line = code[:end_pos].count('\n') + 1

                # Regex doesn't easily capture decorators, parameters, return types accurately
                results.append({
                    'type': CodeElementType.METHOD.value, # Defaulting to METHOD
                    'name': name,
                    'content': content,
                    'class_name': class_name,
                    'range': {'start': {'line': start_line, 'column': 0}, 'end': {'line': end_line, 'column': 0}}, # Column info is lost
                    'decorators': [],
                    'parameters': [],
                    'return_info': {},
                    'definition_start_line': start_line # Approximation
                })
            except IndexError:
                 logger.error(f'Regex match did not contain expected group for name: {match.group(0)}')
            except Exception as e:
                 logger.error(f'Error processing regex match: {e}', exc_info=True)

        return results

    # Override the base method to ensure the correct processing functions are called
    def _extract_with_patterns(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        """Extracts elements, trying TreeSitter, then possibly Regex."""
        current_handler = handler or self.descriptor
        if not current_handler or not (current_handler.tree_sitter_query or current_handler.regexp_pattern):
            logger.error(f'Missing descriptor or patterns for {self.language_code}/{self.ELEMENT_TYPE.value}')
            return []

        elements = []
        tree_sitter_attempted = False
        tree_sitter_error = False

        # TreeSitter extraction phase
        if self._should_attempt_tree_sitter(current_handler):
            tree_sitter_attempted = True
            try:
                self._before_tree_sitter(current_handler)
                elements = self._parse_code_with_tree_sitter(code, current_handler, context)
            except Exception as e:
                self._handle_tree_sitter_exception(e, current_handler)
                elements = []
                tree_sitter_error = True

        # Regex fallback phase
        should_fallback = self._should_fallback_to_regex(tree_sitter_attempted, tree_sitter_error, elements, current_handler)
        if should_fallback and current_handler.regexp_pattern:
            try:
                self._before_regex(current_handler)
                elements = self._parse_code_with_regex(code, current_handler, context)
            except Exception as e:
                self._handle_regex_exception(e, current_handler)
                elements = []

        self._after_extraction(elements, tree_sitter_attempted, tree_sitter_error, should_fallback, current_handler)

        return elements

    def _should_attempt_tree_sitter(self, handler: ElementTypeLanguageDescriptor) -> bool:
        return bool(handler.tree_sitter_query) and self._get_ast_handler() is not None

    def _before_tree_sitter(self, handler: ElementTypeLanguageDescriptor):
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        logger.debug(f'Attempting TreeSitter extraction for {self.language_code} (handler: {handler_type_name}).')

    def _parse_code_with_tree_sitter(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        ast_handler = self._get_ast_handler()
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        root, code_bytes = ast_handler.parse(code)
        query_results = ast_handler.execute_query(handler.tree_sitter_query, root, code_bytes)
        return self._process_tree_sitter_results(query_results, code_bytes, ast_handler, context)

    def _handle_tree_sitter_exception(self, e: Exception, handler: ElementTypeLanguageDescriptor):
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        logger.error(f'Error during TreeSitter extraction for {self.language_code} ({handler_type_name}): {e}', exc_info=False)

    def _should_fallback_to_regex(self, tree_sitter_attempted: bool, tree_sitter_error: bool, elements: List[Dict], handler: ElementTypeLanguageDescriptor) -> bool:
        # Fallback if TreeSitter was not attempted or errored
        return not tree_sitter_attempted or tree_sitter_error

    def _before_regex(self, handler: ElementTypeLanguageDescriptor):
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        logger.debug(f"Using Regex fallback for {self.language_code} (handler: {handler_type_name}).")

    def _parse_code_with_regex(self, code: str, handler: ElementTypeLanguageDescriptor, context: Dict[str, Any]) -> List[Dict]:
        matches = re.finditer(handler.regexp_pattern, code, re.MULTILINE | re.DOTALL)
        return self._process_regex_results(matches, code, context)

    def _handle_regex_exception(self, e: Exception, handler: ElementTypeLanguageDescriptor):
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        logger.error(f"Error during Regex extraction for {self.language_code} (handler: {handler_type_name}): {e}", exc_info=False)

    def _after_extraction(self, elements: List[Dict], tree_sitter_attempted: bool, tree_sitter_error: bool, should_fallback: bool, handler: ElementTypeLanguageDescriptor):
        handler_type_name = handler.element_type.value if handler.element_type else 'unknown_handler'
        if not elements and tree_sitter_attempted and not tree_sitter_error:
            logger.debug(f"TreeSitter extraction for {self.language_code} (handler: {handler_type_name}) returned no elements.")
        elif not elements and should_fallback and handler.regexp_pattern:
            logger.debug(f"Regex extraction for {self.language_code} (handler: {handler_type_name}) returned no elements.")