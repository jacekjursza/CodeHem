# NEW FILE: Extractor for Python property getters (@property)
import logging
from typing import List, Dict, Any, Tuple, Optional # Added Optional
from tree_sitter import Node
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
from codehem.core.engine.ast_handler import ASTHandler # Import ASTHandler for type hint

logger = logging.getLogger(__name__)

@extractor
class PythonPropertyGetterExtractor(TemplateExtractor):
    """ Extracts Python property getters (@property methods). """
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.PROPERTY_GETTER

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process captures from the PROPERTY_GETTER_TEMPLATE query. """
        getters = []
        processed_def_node_ids = set()

        for node, capture_name in query_results:
            definition_node = None
            node_for_range_and_content = None

            if capture_name == 'property_def':
                # The captured node is 'decorated_definition' which includes the decorator
                node_for_range_and_content = node
                definition_node = ast_handler.find_child_by_field_name(node, 'definition')
                if not (definition_node and definition_node.type == 'function_definition'):
                    logger.warning(f"Could not find valid function_definition within property_def capture: {ast_handler.get_node_text(node, code_bytes)}")
                    continue
            elif capture_name == 'property_name':
                # Need to find the containing decorated_definition node for full range/content
                func_def = ast_handler.find_parent_of_type(node, 'function_definition')
                if func_def:
                     parent_decorated = func_def.parent
                     if parent_decorated and parent_decorated.type == 'decorated_definition':
                          # Verify it actually has the @property decorator
                          decorators = self._extract_decorators_simple(ast_handler, parent_decorated, code_bytes)
                          if any(d.get('name') == 'property' for d in decorators):
                               definition_node = func_def
                               node_for_range_and_content = parent_decorated
                          else: continue # Name matched, but not a @property
                     else: continue # Name matched, but not decorated
                else: continue # Name found, but not in a function? Skip.
            else:
                continue # Skip other captures like decorator_name

            if definition_node and node_for_range_and_content and definition_node.id not in processed_def_node_ids:
                common_info = self._extract_common_info(definition_node, node_for_range_and_content, ast_handler, code_bytes)
                if common_info:
                     class_name = self._get_class_name(definition_node, ast_handler, code_bytes)
                     if class_name: # Properties must be in classes
                         decorators = self._extract_decorators_simple(ast_handler, node_for_range_and_content, code_bytes)
                         getter_info = {
                             'type': self.ELEMENT_TYPE.value,
                             'name': common_info['name'],
                             'content': common_info['content'],
                             'range': common_info['range'],
                             'class_name': class_name,
                             'decorators': decorators,
                             'parameters': common_info['parameters'],
                             'return_info': common_info['return_info'],
                             'definition_start_line': common_info.get('definition_start_line', common_info['range']['start']['line']),
                         }
                         getters.append(getter_info)
                         processed_def_node_ids.add(definition_node.id)
                else:
                     logger.warning(f"Failed to extract common info for property getter node id {definition_node.id}")

        return getters

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        # Regex fallback is less reliable for structured info
        getters = []
        logger.debug("Attempting regex fallback for Property Getters.")
        if not self.descriptor or not self.descriptor.regexp_pattern:
             logger.warning("Property getter regex pattern missing.")
             return []
        pattern = self.descriptor.regexp_pattern
        try:
            class_name_context = context.get('class_name') # Get class context if available
            for match in re.finditer(pattern, code, re.MULTILINE | re.DOTALL):
                try:
                    # Extract info based on PROPERTY_GETTER_TEMPLATE regex groups
                    prop_name = match.group(1) # Captured identifier
                    body_content = match.group(2).strip() # Captured body lookahead (approximate)
                    full_content = match.group(0) # Full matched text including decorator
                    start_pos, end_pos = match.span()
                    start_line = code[:start_pos].count('\n') + 1
                    end_line = code[:end_pos].count('\n') + 1

                    # Basic parameter/return parsing from regex signature (less reliable)
                    parameters = [{'name':'self', 'type':None}] # Assume self
                    return_info = {'return_type': None, 'return_values': []} # Cannot reliably get values

                    getter_info = {
                        'type': self.ELEMENT_TYPE.value,
                        'name': prop_name,
                        'content': full_content.strip(),
                        'range': {'start': {'line': start_line, 'column': 0}, 'end': {'line': end_line, 'column': 0}},
                        'class_name': class_name_context, # Use context if available
                        'decorators': [{'name':'property','content':'@property'}], # Assume @property based on regex match
                        'parameters': parameters,
                        'return_info': return_info,
                        'definition_start_line': start_line + 1, # Line after decorator
                    }
                    getters.append(getter_info)
                except IndexError:
                     logger.warning(f"Regex property getter match failed to capture expected group: {match.group(0)}")
                except Exception as e:
                     logger.error(f"Error processing regex property getter match: {e}", exc_info=True)
        except re.error as e:
             logger.error(f"Invalid regex pattern for property getters: {pattern}. Error: {e}")

        return getters

    # Helper methods (can be shared/inherited)
    def _get_class_name(self, node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[str]:
         class_node = ast_handler.find_parent_of_type(node, 'class_definition')
         if class_node:
              name_node = ast_handler.find_child_by_field_name(class_node, 'name')
              if name_node:
                   return ast_handler.get_node_text(name_node, code_bytes)
         return None

    def _extract_common_info(self, definition_node: Node, node_for_range_and_content: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[Dict[str, Any]]:
         # Extracts info like name, params, return, content, range
         info = {}
         name_node = ast_handler.find_child_by_field_name(definition_node, 'name')
         if not name_node: return None
         info['name'] = ast_handler.get_node_text(name_node, code_bytes)

         info['content'] = ast_handler.get_node_text(node_for_range_and_content, code_bytes)
         start = node_for_range_and_content.start_point
         end = node_for_range_and_content.end_point
         info['range'] = {'start': {'line': start[0] + 1, 'column': start[1]}, 'end': {'line': end[0] + 1, 'column': end[1]}}
         info['definition_start_line'] = definition_node.start_point[0] + 1

         info['parameters'] = ExtractorHelpers.extract_parameters(ast_handler, definition_node, code_bytes, is_self_or_this=True)
         info['return_info'] = ExtractorHelpers.extract_return_info(ast_handler, definition_node, code_bytes)
         return info

    def _extract_decorators_simple(self, ast_handler: ASTHandler, node: Node, code_bytes: bytes) -> List[Dict]:
         # Simplified decorator extraction for use within other extractors
         decorators = []
         if node.type == 'decorated_definition':
              for child in node.children:
                   if child.type == 'decorator':
                        name = 'unknown_decorator'
                        content = ast_handler.get_node_text(child, code_bytes)
                        if child.child_count > 1:
                             name_node = child.child(1)
                             name = ast_handler.get_node_text(name_node, code_bytes)
                        decorators.append({'name': name, 'content': content})
         return decorators