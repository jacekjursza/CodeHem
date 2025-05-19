# NEW FILE: Extractor for Python property setters (@name.setter)
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from tree_sitter import Node
from codehem.core.extractors.extraction_base import TemplateExtractor, ExtractorHelpers
from codehem.models.enums import CodeElementType
from codehem.core.registry import extractor
from codehem.core.engine.ast_handler import ASTHandler

logger = logging.getLogger(__name__)

@extractor
class PythonPropertySetterExtractor(TemplateExtractor):
    """ Extracts Python property setters (@name.setter methods). """
    LANGUAGE_CODE = 'python'
    ELEMENT_TYPE = CodeElementType.PROPERTY_SETTER

    def _process_tree_sitter_results(self, query_results: List[Tuple[Node, str]], code_bytes: bytes, ast_handler: ASTHandler, context: Dict[str, Any]) -> List[Dict]:
        """ Process captures from the PROPERTY_SETTER_TEMPLATE query. """
        setters = []
        processed_def_node_ids = set()

        # Query captures 'property_setter_def' -> decorated_definition node
        # It also captures 'property_name' inside the function def for verification
        for decorated_def_node, capture_name in query_results:
            if capture_name == 'property_setter_def':
                definition_node = ast_handler.find_child_by_field_name(decorated_def_node, 'definition')
                if not (definition_node and definition_node.type == 'function_definition'):
                    logger.warning(f"Could not find valid function_definition within property_setter_def capture: {ast_handler.get_node_text(decorated_def_node, code_bytes)}")
                    continue

                if definition_node.id not in processed_def_node_ids:
                    common_info = self._extract_common_info(definition_node, decorated_def_node, ast_handler, code_bytes)
                    if common_info:
                        class_name = self._get_class_name(definition_node, ast_handler, code_bytes)
                        if class_name: # Must be in a class
                            decorators = self._extract_decorators_simple(ast_handler, decorated_def_node, code_bytes)

                            # Verify decorator name matches method name (query also does this with #eq?)
                            expected_decorator = f"{common_info['name']}.setter"
                            if not any(d.get('name') == expected_decorator for d in decorators):
                                logger.warning(f"Node captured as setter for '{common_info['name']}' but decorator mismatch: {[d.get('name') for d in decorators]}")
                                continue # Skip if decorator doesn't match

                            setter_info = {
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
                            setters.append(setter_info)
                            processed_def_node_ids.add(definition_node.id)
                    else:
                        logger.warning(f"Failed to extract common info for property setter node id {definition_node.id}")

        return setters

    def _process_regex_results(self, matches: Any, code: str, context: Dict[str, Any]) -> List[Dict]:
        # Regex fallback is less reliable
        setters = []
        logger.debug("Attempting regex fallback for Property Setters.")
        if not self.descriptor or not self.descriptor.regexp_pattern:
             logger.warning("Property setter regex pattern missing.")
             return []
        pattern = self.descriptor.regexp_pattern
        try:
            class_name_context = context.get('class_name')
            # Regex needs to capture property name from decorator AND method name
            # The current template regex might need adjustment for this capture.
            # Assuming group(1) is method name, need logic to find decorator name.
            for match in re.finditer(pattern, code, re.MULTILINE | re.DOTALL):
                try:
                    method_name = match.group(1) # Method name
                    full_content = match.group(0) # Full matched text
                    start_pos, end_pos = match.span()
                    start_line = code[:start_pos].count('\n') + 1
                    end_line = code[:end_pos].count('\n') + 1

                    # Extract decorator name from the full content (approximate)
                    decorator_name = f"@{method_name}.setter" # Assume correct format
                    decorator_content = decorator_name # Approximate content

                    parameters = [{'name':'self', 'type':None}, {'name':'value', 'type':None}] # Assume self, value
                    return_info = {'return_type': 'None', 'return_values': []} # Assume None return

                    setter_info = {
                        'type': self.ELEMENT_TYPE.value,
                        'name': method_name,
                        'content': full_content.strip(),
                        'range': {'start': {'line': start_line, 'column': 0}, 'end': {'line': end_line, 'column': 0}},
                        'class_name': class_name_context,
                        'decorators': [{'name': decorator_name, 'content': decorator_content}],
                        'parameters': parameters,
                        'return_info': return_info,
                        'definition_start_line': start_line + 1, # Line after decorator approx
                    }
                    setters.append(setter_info)
                except IndexError:
                     logger.warning(f"Regex property setter match failed to capture expected group: {match.group(0)}")
                except Exception as e:
                     logger.error(f"Error processing regex property setter match: {e}", exc_info=True)
        except re.error as e:
            logger.error(f"Invalid regex pattern for property setters: {pattern}. Error: {e}")
        return setters

    # Helper methods (shared with getter extractor)
    def _get_class_name(self, node: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[str]:
         class_node = ast_handler.find_parent_of_type(node, 'class_definition')
         if class_node:
              name_node = ast_handler.find_child_by_field_name(class_node, 'name')
              if name_node:
                   return ast_handler.get_node_text(name_node, code_bytes)
         return None

    def _extract_common_info(self, definition_node: Node, node_for_range_and_content: Node, ast_handler: ASTHandler, code_bytes: bytes) -> Optional[Dict[str, Any]]:
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
         decorators = []
         if node.type == 'decorated_definition':
              for child in node.children:
                   if child.type == 'decorator':
                        content = ast_handler.get_node_text(child, code_bytes)
                        name = 'unknown_decorator'
                        # Simple name extraction from @name or @name.attr
                        if child.child_count > 1:
                             name_node = child.child(1)
                             name = ast_handler.get_node_text(name_node, code_bytes)
                        decorators.append({'name': name, 'content': content})
         return decorators