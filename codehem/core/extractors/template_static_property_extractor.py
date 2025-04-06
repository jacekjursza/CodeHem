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

    def _get_parent_class_name(self, node: Node, ast_handler: Any, code_bytes: bytes) -> Optional[str]:
        """Finds the name of the containing class definition."""
        class_node_types = ['class_definition', 'class_declaration']
        # Start search from the block's parent (which should be the class_definition)
        current_node = node.parent
        while current_node:
            if current_node.type in class_node_types:
                name_node = ast_handler.find_child_by_field_name(current_node, 'name')
                if name_node:
                    return ast_handler.get_node_text(name_node, code_bytes)
                else:
                    # Fallback for grammars where name might be a direct identifier child
                    for child in current_node.children:
                         if child.type in ['identifier', 'type_identifier']:
                            return ast_handler.get_node_text(child, code_bytes)
                return None # Found class node but no name
            # Stop searching upwards if we leave the class structure unexpectedly
            if current_node.type == 'module':
                 break
            current_node = current_node.parent
        return None

    # Keep _get_class_name for potential direct calls if needed, although _get_parent_class_name is used below
    def _get_class_name(self, node, ast_handler, code_bytes):
        return self._get_parent_class_name(node, ast_handler, code_bytes)

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: Any, context: Dict[str, Any]) -> List[Dict]:
        """Process tree-sitter query results for static properties using the @class_block query."""
        properties = []
        logger.debug(f"Processing {len(query_results)} captures from @class_block query.")

        for block_node, capture_name in query_results:
            if capture_name != 'class_block':
                logger.warning(f"Unexpected capture '{capture_name}' in static property extractor. Expected '@class_block'.")
                continue

            # Get class name from the parent of the block node
            class_name = self._get_parent_class_name(block_node, ast_handler, code_bytes)
            if not class_name:
                 logger.debug(f"Skipping block node (ID: {block_node.id}) because parent class name could not be determined.")
                 continue

            logger.debug(f"Processing children of @class_block for class '{class_name}' (Node ID: {block_node.id})")

            # Iterate through direct children of the captured block node
            for child_node in block_node.named_children:
                prop_name_text = None
                prop_value_text = None
                prop_type_text = None # Default to None (or 'N/A' if preferred for logging)
                assignment_node = None # The core assignment node
                node_for_range = child_node # Use the child node (e.g., expression_statement) for range/content

                # Determine the actual assignment node and if it might have a type hint
                is_potentially_typed = False
                if child_node.type == 'assignment':
                    assignment_node = child_node
                elif child_node.type == 'typed_assignment': # Direct typed_assignment at class level (less common)
                     assignment_node = child_node
                     is_potentially_typed = True # Mark that it MIGHT have a type field
                elif child_node.type == 'expression_statement' and child_node.named_child_count == 1:
                    inner_node = child_node.named_child(0)
                    if inner_node.type == 'assignment':
                        assignment_node = inner_node
                        logger.debug(f"  Found assignment within expression_statement.")
                        # An assignment node itself might have a type field in some Python ASTs
                        if assignment_node.child_by_field_name('type'):
                            is_potentially_typed = True
                    elif inner_node.type == 'typed_assignment': # If grammar uses this inside expression_statement
                         assignment_node = inner_node
                         is_potentially_typed = True
                         logger.debug(f"  Found typed_assignment within expression_statement.")
                    else:
                         logger.debug(f"  Inner node type '{inner_node.type}' within expression_statement skipped.")
                else:
                    logger.debug(f"  Child node type '{child_node.type}' skipped.")

                # If we found a relevant assignment node, extract details
                if assignment_node:
                    left_node = assignment_node.child_by_field_name('left')
                    # Value is typically in 'right' for class level, but check 'value' as fallback
                    value_node = assignment_node.child_by_field_name('right') or assignment_node.child_by_field_name('value')
                    type_node = assignment_node.child_by_field_name('type') # Check if type hint field exists

                    # Extract Name
                    if left_node and left_node.type == 'identifier':
                        prop_name_text = ast_handler.get_node_text(left_node, code_bytes)

                    # Extract Value
                    if value_node:
                        prop_value_text = ast_handler.get_node_text(value_node, code_bytes)
                    else:
                         prop_value_text = None # Value might be missing

                    # Extract Type ONLY if type_node was found
                    if type_node:
                        prop_type_text = ast_handler.get_node_text(type_node, code_bytes)

                    # Construct the result dictionary if name was found
                    if prop_name_text:
                        content = ast_handler.get_node_text(node_for_range, code_bytes) # Use outer node for full content
                        start_point = node_for_range.start_point
                        end_point = node_for_range.end_point
                        prop_info = {
                            'type': CodeElementType.STATIC_PROPERTY.value,
                            'name': prop_name_text,
                            'content': content.strip(), # Store stripped content
                            'class_name': class_name,
                            'range': {
                                'start': {'line': start_point[0] + 1, 'column': start_point[1]},
                                'end': {'line': end_point[0] + 1, 'column': end_point[1]}
                            },
                            'value_type': prop_type_text,
                            'value': prop_value_text, # Store raw value text
                            # 'definition_start_line': start_point[0] + 1 # Less critical now
                        }
                        properties.append(prop_info)
                        logger.debug(f"  -> Extracted Static Property: {class_name}.{prop_name_text} (Type: {prop_type_text}, Value: {prop_value_text})")
                    else:
                         logger.warning(f"  Could not extract name from assignment node: {ast_handler.get_node_text(assignment_node, code_bytes)}")

        logger.debug(f"Finished processing @class_block captures. Found {len(properties)} static properties.")
        return properties

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        """Process regex match results for static properties (fallback)."""
        properties = []
        # This regex fallback might still be needed if TreeSitter parsing fails for unexpected reasons.
        # Keep the warning but ensure basic functionality.
        logger.warning('Using Regex fallback for static properties. This is less accurate.')
        class_name_context = context.get('class_name') if context else None # Use provided context if available

        # Use the regex pattern from the handler
        pattern = self.descriptor.regexp_pattern
        if not pattern:
            logger.error("Regex pattern for static property is missing in descriptor.")
            return []

        try:
            # Find all matches in the relevant code scope (might need context adjustment in real use)
             for match in re.finditer(pattern, code, re.MULTILINE):
                try:
                     # Regex groups depend on the defined pattern in STATIC_PROPERTY_TEMPLATE
                     prop_name = match.group(1)
                     prop_value = match.group(2).strip() if len(match.groups()) >= 2 else None # Assuming value is group 2
                     content = match.group(0)
                     start_pos, end_pos = match.span()
                     start_line = code[:start_pos].count('\n') + 1
                     end_line_content = content.rstrip('\n\r')
                     end_line = start_line + end_line_content.count('\n')

                     # Simple type guessing based on value (same as before)
                     value_type = None
                     if prop_value:
                         if prop_value.isdigit():
                             value_type = 'int'
                         elif prop_value.replace('.', '', 1).isdigit():
                             value_type = 'float'
                         elif prop_value in ['True', 'False']:
                             value_type = 'bool'
                         elif prop_value.startswith('"') and prop_value.endswith('"') or (prop_value.startswith("'") and prop_value.endswith("'")):
                             value_type = 'str'

                     prop_info = {
                         'type': CodeElementType.STATIC_PROPERTY.value,
                         'name': prop_name,
                         'content': content.strip(),
                         'class_name': class_name_context, # Assign class context if available
                         'range': {'start': {'line': start_line, 'column': 0}, 'end': {'line': end_line, 'column': 0}}, # Column info from regex is hard
                         'value_type': value_type,
                         'value': prop_value
                     }
                     properties.append(prop_info)
                except IndexError:
                    logger.error(f'Regex static property match missing expected group: {match.group(0)}')
                except Exception as e:
                    logger.error(f'Error processing regex static property match: {e}', exc_info=True)
        except re.error as e:
            logger.error(f"Invalid regex pattern for static property fallback: {pattern}. Error: {e}")

        return properties