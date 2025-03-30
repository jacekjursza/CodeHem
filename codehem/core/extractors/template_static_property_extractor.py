# codehem/core/extractors/template_static_property_extractor.py

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from tree_sitter import Node
from codehem.core.extractors.extraction_base import TemplateExtractor
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
from codehem.models.element_type_descriptor import ElementTypeLanguageDescriptor
logger = logging.getLogger(__name__)

@extractor
class TemplateStaticPropertyExtractor(TemplateExtractor):
    """Template implementation for static class property extraction."""
    ELEMENT_TYPE = CodeElementType.STATIC_PROPERTY

    # --- Helper moved from ExtractorHelpers for direct use ---
    def _get_parent_class_name(self, node: Node, ast_handler: Any, code_bytes: bytes) -> Optional[str]:
        """Finds the name of the containing class definition."""
        class_node_types = ['class_definition', 'class_declaration']
        current_node = node.parent
        while current_node:
            if current_node.type in class_node_types:
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node:
                    return ast_handler.get_node_text(name_node, code_bytes)
                else:
                    # Fallback for potential different name node types/structures
                    for child in current_node.children:
                        if child.type in ['identifier', 'type_identifier']:
                            return ast_handler.get_node_text(child, code_bytes)
                return None # Found class node but no name
            # Stop searching up if we hit a block that's not inside a class or the file root
            if current_node.type == 'block' and current_node.parent and (current_node.parent.type not in class_node_types):
                break
            current_node = current_node.parent
        return None

    # Use the helper method above
    def _get_class_name(self, node, ast_handler, code_bytes):
         # Removed context dependency here, rely solely on AST structure
         return self._get_parent_class_name(node, ast_handler, code_bytes)

    # --- Updated _process_tree_sitter_results to handle new query ---
    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: Any, context: Dict[str, Any]) -> List[Dict]:
        """Process tree-sitter query results for static properties using the revised query."""
        properties = []
        # Store results keyed by the main statement node ID to gather all parts
        node_results: Dict[int, Dict[str, Any]] = {}

        # --- Identify main statement nodes first ---
        main_statement_nodes = {}
        for node, capture_name in query_results:
             if capture_name in ['static_prop_def', 'static_prop_def_direct']:
                 # Make sure we're getting the correct node (expression_statement or assignment)
                 if node.type == 'expression_statement' or node.type == 'assignment':
                      main_statement_nodes[node.id] = node
                 else:
                      logger.warning(f"Unexpected node type '{node.type}' captured as main statement: {ast_handler.get_node_text(node, code_bytes)}")

        # --- Iterate through all captures and associate with main nodes ---
        for node, capture_name in query_results:
            main_node_id = None
            main_node = None

            # Find the corresponding main statement node for this capture
            current = node
            while current:
                if current.id in main_statement_nodes:
                    main_node_id = current.id
                    main_node = main_statement_nodes[main_node_id]
                    break
                if current.type in ['block', 'class_definition', 'module']: # Stop searching up
                     break
                current = current.parent

            # Skip captures that aren't part of identified main statements
            if not main_node_id or not main_node:
                 if capture_name not in ['static_prop_def', 'static_prop_def_direct']:
                     pass # Be less verbose about skipped sub-captures
                 continue

            # Initialize the result dict if this is the first time seeing this statement node
            if main_node_id not in node_results:
                 class_name = self._get_class_name(main_node, ast_handler, code_bytes) # Call using the correct signature
                 if class_name: # Only proceed if we found a class context
                     node_results[main_node_id] = {
                         'node_id': main_node_id,
                         'type': CodeElementType.STATIC_PROPERTY.value,
                         'name': None, # Will be filled by @prop_name
                         'content': ast_handler.get_node_text(main_node, code_bytes),
                         'class_name': class_name,
                         'range': {
                             'start': {'line': main_node.start_point[0] + 1, 'column': main_node.start_point[1]},
                             'end': {'line': main_node.end_point[0] + 1, 'column': main_node.end_point[1]}
                         },
                         'value_type': None, # Will be filled by @prop_type if present
                         'value': None, # Will be filled by @prop_value
                         'definition_start_line': main_node.start_point[0] + 1
                     }
                 else:
                     # Log if found outside a class, but don't store it
                     logger.debug(f"Static property-like node found outside class context? Node: {ast_handler.get_node_text(main_node, code_bytes)}")
                     # Ensure the ID isn't processed further by adding an empty placeholder
                     if main_node_id not in node_results: node_results[main_node_id] = {}

            # Update the dictionary with captured parts if the entry exists (i.e., is within a class)
            if main_node_id in node_results and node_results[main_node_id]:
                if capture_name == 'prop_name':
                    # Avoid overwriting if already found (e.g., from different parts of the query)
                    if node_results[main_node_id]['name'] is None:
                         node_results[main_node_id]['name'] = ast_handler.get_node_text(node, code_bytes)
                elif capture_name == 'prop_type':
                     if node_results[main_node_id]['value_type'] is None:
                          node_results[main_node_id]['value_type'] = ast_handler.get_node_text(node, code_bytes)
                elif capture_name == 'prop_value':
                     if node_results[main_node_id]['value'] is None:
                          node_results[main_node_id]['value'] = ast_handler.get_node_text(node, code_bytes)
                          # Optional basic type inference if not explicitly typed
                          # if node_results[main_node_id]['value_type'] is None:
                          #     # Basic type inference can go here if desired
                          #     pass

        # Finalize and collect valid results
        for result in node_results.values():
             # Ensure it's a valid entry created within a class context
             if result and result.get('name') and result.get('class_name'):
                logger.debug(f"  Extracted static property: {result['class_name']}.{result['name']} (type: {result['value_type']}, value: {result.get('value')})")
                result.pop('node_id', None) # Remove internal tracking ID
                properties.append(result)
             # Optionally log skipped entries if needed for debugging
             # elif result: logger.warning(f"Skipping incomplete static property entry: missing name or class_name. Content: {result.get('content')}")

        return properties

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """Process regex match results for static properties (fallback)."""
        properties = []
        logger.warning('Regex fallback for static properties is basic and might be inaccurate for complex cases or context.')

        # Attempt to find class context using regex (less reliable)
        class_name_context = None
        if context and 'class_name' in context:
             class_name_context = context['class_name']
        # This regex approach for class name is highly simplified and fragile
        # A better approach would involve passing class context if available from TreeSitter class extraction

        for match in matches:
            try:
                prop_name = match.group(1)
                # Group 2 now captures the value part after '=' based on the updated regex
                prop_value = match.group(2).strip() if len(match.groups()) >= 2 else None
                content = match.group(0) # The whole matched line/statement
                start_pos, end_pos = match.span()
                start_line = code[:start_pos].count('\n') + 1
                # Regex might capture trailing newline, adjust end_line if needed
                end_line_content = content.rstrip('\n\r')
                end_line = start_line + end_line_content.count('\n')

                # Simplistic type inference from value if needed (and no type hint matched)
                value_type = None
                # Example basic inference (can be expanded)
                if prop_value:
                    if prop_value.isdigit(): value_type = 'int'
                    elif prop_value.replace('.', '', 1).isdigit(): value_type = 'float'
                    elif prop_value in ['True', 'False']: value_type = 'bool'
                    elif (prop_value.startswith('"') and prop_value.endswith('"')) or \
                         (prop_value.startswith("'") and prop_value.endswith("'")): value_type = 'str'

                prop_info = {
                     'type': CodeElementType.STATIC_PROPERTY.value,
                     'name': prop_name,
                     'content': content.strip(),
                     'class_name': class_name_context, # Assign context if available, otherwise None
                     'range': {'start': {'line': start_line, 'column': 0}, 'end': {'line': end_line, 'column': 0}}, # Column info is lost in regex
                     'value_type': value_type, # Assign inferred type if applicable
                     'value': prop_value, # Store the extracted value
                     'definition_start_line': start_line
                }
                properties.append(prop_info)
            except IndexError:
                logger.error(f'Regex static property match missing group: {match.group(0)}')
            except Exception as e:
                logger.error(f'Error processing regex static property match: {e}', exc_info=True)
        return properties